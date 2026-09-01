"""F-02 · 文档上传三级一致性校验（SECURITY_BASELINE §4）。

挂接点＝官方 ``WAGTAILDOCS_DOCUMENT_FORM_BASE``（wagtail.documents.forms.
get_document_base_form 读此设置构造上传表单）：Wagtail 7.4.2 的单文件上传、
多文件上传与编辑替换三条后台路径均经 ``get_document_form`` 构建表单
（wagtail/documents/views/documents.py、views/multiple.py），故此单一收口
覆盖全部 wagtaildocs 入口，不改 Wagtail 核心。

校验分层（SB §4.2）：

① 扩展名——``Document.clean()`` 内 FileExtensionValidator（官方机制），
   由 ``WAGTAILDOCS_EXTENSIONS``（SB §4.1 冻结清单）约束，本模块不重复；
② 浏览器声明 MIME——仅用于拒绝明显矛盾（如声明 text/html 的 .pdf），
   不单独放行；generic/octet-stream 类无约束力声明一律忽略；
③ 内容签名——filetype 库正向识别 pdf/docx/xlsx/pptx；老式复合容器
   doc/xls/ppt filetype 1.2.0 不识别，按 CFB 容器魔数比对；识别失败一律
   拒绝（白名单语义：必须正向确认，不做宽松兜底）。

文件名治理（SB §4.4）：路径形式拒绝（../、绝对路径、盘符）；控制字符
剥离；超 255 字节保留扩展名截断。错误文案面向编辑人员（中文，不含
服务端路径/堆栈/配置），安全矩阵回归见 tests/test_upload_validation.py。
"""

import os
import re
import unicodedata
import zipfile

import filetype
from django.conf import settings
from django.core.exceptions import ValidationError
from wagtail.documents.forms import BaseDocumentForm

# ② 各扩展名的规范 MIME：声明凡可识别且不匹配＝矛盾拒绝（SB §4.2 第二层）。
MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# ③ filetype 1.2.0 可正向识别的扩展名；doc/xls/ppt 走 CFB 魔数比对。
SIGNATURE_DETECTED_EXTENSIONS = frozenset({"pdf", "docx", "xlsx", "pptx"})
CFB_EXTENSIONS = frozenset({"doc", "xls", "ppt"})
CFB_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# ② 浏览器常发送但不具约束力的 generic 声明：忽略，不参与矛盾判定。
GENERIC_DECLARED_TYPES = frozenset(
    {
        "",
        "application/octet-stream",
        "application/binary",
        "application/unknown",
        "application/download",
        "application/x-download",
        "application/force-download",
        "binary/octet-stream",
    }
)

# 签名识别读取头部字节量（OOXML 容器标记集中于首个本地头部，64KiB 充裕）。
SIGNATURE_HEAD_BYTES = 64 * 1024

MSG_SIGNATURE = "无法识别文件内容，或文件内容与扩展名不一致；请确认文件未损坏后重新导出再上传。"
MSG_MIME_CONFLICT = "声明的文件类型与扩展名不一致；请重新导出文件后再上传。"
MSG_PATH_FORM = "文件名不能包含路径信息（如 ../、绝对路径或盘符），请重命名后再上传。"
MSG_NAME_EMPTY = "文件名不能为空或全为空白字符。"


def validate_filename(name: str) -> str:
    """SB §4.4 文件名治理：路径形式拒绝、控制字符剥离、超限保留扩展名截断。

    返回净化后的文件名（写回上传对象后供存储层使用）。
    """
    if not name:
        raise ValidationError(MSG_NAME_EMPTY)
    if "/" in name or "\\" in name or re.match(r"^[A-Za-z]:", name) or name in (".", ".."):
        raise ValidationError(MSG_PATH_FORM)
    cleaned = "".join(ch for ch in name if unicodedata.category(ch) != "Cc").strip()
    if not cleaned:
        raise ValidationError(MSG_NAME_EMPTY)
    return _truncate_preserving_extension(cleaned)


def _truncate_preserving_extension(name: str, max_bytes: int = 255) -> str:
    """超 255 字节截断存储名，保留扩展名（SB §4.4）。"""
    if len(name.encode("utf-8")) <= max_bytes:
        return name
    stem, dot, extension = name.rpartition(".")
    suffix = f".{extension}" if dot else ""
    if len(suffix.encode("utf-8")) >= max_bytes:
        # 扩展名自身异常超长：放弃保留，整体硬截（理论边缘）。
        return name.encode("utf-8")[:max_bytes].decode("utf-8", "ignore")
    trimmed = stem if dot else name
    while trimmed and len((trimmed + suffix).encode("utf-8")) > max_bytes:
        trimmed = trimmed[:-1]
    if not trimmed:
        return name.encode("utf-8")[:max_bytes].decode("utf-8", "ignore")
    return trimmed + suffix


# OPC 容器部件前缀：zipfile 中央目录兜底判定用（docx/xlsx/pptx 各自的包部件）。
OOXML_PART_PREFIX = {"docx": "word/", "xlsx": "xl/", "pptx": "ppt/"}


def _ooxml_contains_part(file, extension: str) -> bool:
    """PK 容器内 OPC 部件存在性（zipfile 只读中央目录，不整读文件）。

    filetype 的 OOXML 匹配器按头部窗口搜标记，非常规打包器可能把部件
    名推到窗口之外——此兜底给出精确判定，避免误拒真实 Office 文件。
    """
    prefix = OOXML_PART_PREFIX[extension]
    try:
        with zipfile.ZipFile(file) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and any(name.startswith(prefix) for name in names)


def validate_file_content(file, extension: str) -> None:
    """③内容签名正向确认（识别失败即拒绝）＋②声明 MIME 矛盾拒绝。

    签名在先：对内容不符的文件给出「内容与扩展名不一致」的准确语义，
    ②仅对签名成立但声明类型矛盾的文件给出「声明类型不一致」。
    """
    expected_mime = MIME_BY_EXTENSION.get(extension)
    head = file.read(SIGNATURE_HEAD_BYTES)
    file.seek(0)

    if extension in CFB_EXTENSIONS:
        if not head.startswith(CFB_MAGIC):
            raise ValidationError(MSG_SIGNATURE)
    elif extension in SIGNATURE_DETECTED_EXTENSIONS:
        kind = filetype.guess(head)
        signature_ok = (
            kind is not None and kind.extension == extension and kind.mime == expected_mime
        )
        if not signature_ok and head[:2] == b"PK":
            signature_ok = _ooxml_contains_part(file, extension)
        if not signature_ok:
            raise ValidationError(MSG_SIGNATURE)

    declared = (getattr(file, "content_type", "") or "").split(";")[0].strip().lower()
    if (
        expected_mime
        and declared
        and declared not in GENERIC_DECLARED_TYPES
        and declared != expected_mime
    ):
        raise ValidationError(MSG_MIME_CONFLICT)


class ValidatedDocumentForm(BaseDocumentForm):
    """F-02 收口表单：文件名治理＋声明 MIME＋内容签名三级一致性（SB §4）。

    校验挂在 ``_post_clean``（模型层 ①扩展名校验完成之后）：既不与官方
    ``Document.clean()`` 的扩展名错误叠加，也避免 ``add_error`` 驱逐
    ``cleaned_data["file"]`` 引发模型侧二次噪音错误。
    """

    def _post_clean(self):
        super()._post_clean()
        allowlist = getattr(settings, "WAGTAILDOCS_EXTENSIONS", None) or []
        # 仅校验本次新上传的文件（编辑保留原文件的请求 file 字段无变更）。
        if "file" not in self.changed_data:
            return
        uploaded = self.cleaned_data.get("file")
        if uploaded is None:
            return
        try:
            uploaded.name = validate_filename(uploaded.name)
            extension = os.path.splitext(uploaded.name)[1].lstrip(".").lower()
            if extension in allowlist:
                validate_file_content(uploaded, extension)
        except ValidationError as error:
            self.add_error("file", error)
