"""F-02 上传三级一致性回归（SECURITY_BASELINE §4 / SB-05 安全矩阵）。

断言面：①扩展名白名单（官方 FileExtensionValidator 经收窄清单生效）；
②声明 MIME 仅拒明显矛盾、generic 声明不误伤；③内容签名正向识别
（filetype：pdf/docx/xlsx/pptx；CFB 魔数：doc/xls/ppt），伪装/损坏一律拒。
文件名治理（SB §4.4）：路径形式拒绝、控制字符剥离、超限保留扩展名截断。
错误文案不暴露服务端路径/堆栈/配置。挂接点＝WAGTAILDOCS_DOCUMENT_FORM_BASE
单收口（三条后台上传路径共用的官方覆盖机制）。
"""

import io
import zipfile

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from wagtail.documents.forms import get_document_base_form, get_document_form
from wagtail.documents.models import Document
from wagtail.models import Collection

from peiligo.upload_validation import (
    CFB_EXTENSIONS,
    CFB_MAGIC,
    MIME_BY_EXTENSION,
    SIGNATURE_DETECTED_EXTENSIONS,
    SIGNATURE_HEAD_BYTES,
    ValidatedDocumentForm,
    validate_file_content,
    validate_filename,
)


def _zip_bytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return buf.getvalue()


PDF_BYTES = (
    b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF\n"
)
DOCX_BYTES = _zip_bytes(
    [("[Content_Types].xml", "<Types/>"), ("word/document.xml", "<w:document/>")]
)
XLSX_BYTES = _zip_bytes([("[Content_Types].xml", "<Types/>"), ("xl/workbook.xml", "<workbook/>")])
PPTX_BYTES = _zip_bytes(
    [("[Content_Types].xml", "<Types/>"), ("ppt/presentation.xml", "<p:presentation/>")]
)
PLAIN_ZIP_BYTES = _zip_bytes([("readme.txt", "hello")])
# 标记越过头部分块的 OOXML（首个条目远超 64KiB）：须被整文件兜底识别而非误拒。
DOCX_MARKER_BEYOND_HEAD_BYTES = _zip_bytes(
    [
        ("padding.bin", "A" * (SIGNATURE_HEAD_BYTES * 2)),
        ("[Content_Types].xml", "<Types/>"),
        ("word/document.xml", "<w:document/>"),
    ]
)
CFB_BYTES = CFB_MAGIC + b"\x00" * 512
TEXT_BYTES = "这是一段伪装成附件的纯文本。".encode()


class ImageExtensionFreezeTests(TestCase):
    """R 审查 M2：图片面白名单按 SB §4.1 冻结集收口（png/jpg/webp）。

    Wagtail 缺省另放行 avif/gif，超出冻结集；jpeg 为 jpg 同格式别名
    （PRD 白名单按格式口径，非格式扩充）。
    """

    def test_settings_freeze_image_extensions(self):
        self.assertEqual(settings.WAGTAILIMAGES_EXTENSIONS, ["jpg", "jpeg", "png", "webp"])


class UploadFixtureTests(TestCase):
    """经收口表单的完整校验流（含模型层扩展名约束）。"""

    def _validated(self, name, content, content_type=None):
        form_class = get_document_form(Document)  # 生产同源工厂（含模型绑定）
        root = Collection.get_first_root_node()
        upload = SimpleUploadedFile(name, content, content_type=content_type)
        return form_class(data={"title": "上传测试", "collection": root.pk}, files={"file": upload})


class DocumentUploadMatrixTests(UploadFixtureTests):
    """SB-05：扩展名 × 内容 × 声明 MIME 一致性矩阵（经表单全链路）。"""

    def _reject_fragment(self, form, fragment):
        self.assertFalse(form.is_valid())
        joined = " ".join(form.errors.get("file", []))
        self.assertIn(fragment, joined)
        return joined

    def test_real_documents_pass(self):
        cases = [
            ("通知.pdf", PDF_BYTES, "application/pdf"),
            ("手册.docx", DOCX_BYTES, MIME_BY_EXTENSION["docx"]),
            ("台账.xlsx", XLSX_BYTES, MIME_BY_EXTENSION["xlsx"]),
            ("演示.pptx", PPTX_BYTES, MIME_BY_EXTENSION["pptx"]),
            ("老文档.doc", CFB_BYTES, MIME_BY_EXTENSION["doc"]),
            ("老表格.xls", CFB_BYTES, MIME_BY_EXTENSION["xls"]),
            ("老幻灯.ppt", CFB_BYTES, MIME_BY_EXTENSION["ppt"]),
        ]
        for name, content, content_type in cases:
            with self.subTest(extension=name.rsplit(".", 1)[1]):
                form = self._validated(name, content, content_type)
                self.assertTrue(form.is_valid(), form.errors)

    def test_generic_declared_mime_accepted(self):
        form = self._validated("通知.pdf", PDF_BYTES, "application/octet-stream")
        self.assertTrue(form.is_valid(), form.errors)

    def test_disguised_text_rejected(self):
        form = self._validated("fake.pdf", TEXT_BYTES)
        self._reject_fragment(form, "无法识别文件内容")

    def test_extension_not_in_allowlist_rejected(self):
        form = self._validated("说明.txt", TEXT_BYTES)
        joined = self._reject_fragment(form, "txt")
        self.assertIn("doc", joined)  # 冻结清单可见（编辑可自纠）

    def test_browser_mime_conflict_rejected(self):
        form = self._validated("通知.pdf", PDF_BYTES, "text/html")
        self._reject_fragment(form, "声明的文件类型与扩展名不一致")

    def test_plain_zip_named_docx_rejected(self):
        form = self._validated("假文档.docx", PLAIN_ZIP_BYTES, "application/zip")
        self._reject_fragment(form, "无法识别文件内容")

    def test_cfb_named_pdf_rejected(self):
        form = self._validated("假pdf.pdf", CFB_BYTES)
        self._reject_fragment(form, "无法识别文件内容")

    def test_ooxml_marker_beyond_head_still_accepted(self):
        form = self._validated("大文档.docx", DOCX_MARKER_BEYOND_HEAD_BYTES)
        self.assertTrue(form.is_valid(), form.errors)

    def test_oversize_rejected_at_frozen_20mib(self):
        oversized = PDF_BYTES + b"\x00" * (20 * 1024 * 1024 + 1)
        form = self._validated("超大.pdf", oversized, "application/pdf")
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_error_messages_reveal_no_internals(self):
        cases = [
            ("fake.pdf", TEXT_BYTES, None),
            ("假文档.docx", PLAIN_ZIP_BYTES, "application/zip"),
            ("通知.pdf", PDF_BYTES, "text/html"),
            ("说明.txt", TEXT_BYTES, None),
        ]
        for name, content, content_type in cases:
            with self.subTest(name=name):
                form = self._validated(name, content, content_type)
                form.is_valid()
                joined = " ".join(form.errors.get("file", []))
                for leak in ("Traceback", "/Users", "/srv", ".py", "settings", "DJANGO"):
                    self.assertNotIn(leak, joined)


class FilenameGovernanceTests(UploadFixtureTests):
    """SB §4.4：路径形式拒绝／控制字符剥离／超限保留扩展名截断。"""

    def test_path_forms_rejected_by_project_validator(self):
        for name in (
            "../passwd.pdf",
            "a/../../b.pdf",
            "/etc/passwd.pdf",
            "C:\\evil.pdf",
            "a\\b.pdf",
            "..",
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    validate_filename(name)

    def test_django_upstream_already_strips_or_rejects_paths(self):
        """平台事实：Django UploadedFile 构造期即剥离目录成分／拒绝 ".."——
        项目校验器为纵深防御层，真实 multipart 上传的路径形式到不了表单。"""
        self.assertEqual(SimpleUploadedFile("../passwd.pdf", b"x").name, "passwd.pdf")
        with self.assertRaises(SuspiciousFileOperation):
            SimpleUploadedFile("..", b"x")

    def test_drive_letter_path_rejected_at_form(self):
        """盘符前缀（反斜杠形式）在 POSIX 上不被 Django 上游剥离——收口层拒绝。"""
        form = self._validated("C:\\evil.pdf", PDF_BYTES)
        joined = " ".join(form.errors.get("file", []))
        self.assertIn("路径", joined)

    def test_control_chars_stripped_and_upload_accepted(self):
        form = self._validated("report\x00\x1b note.pdf", PDF_BYTES)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.files["file"].name, "report note.pdf")

    def test_overlong_name_truncated_preserving_extension(self):
        form = self._validated("很" * 300 + ".pdf", PDF_BYTES)
        self.assertTrue(form.is_valid(), form.errors)
        stored = form.files["file"].name
        self.assertTrue(stored.endswith(".pdf"))
        self.assertLessEqual(len(stored.encode("utf-8")), 255)

    def test_unit_truncate_preserving_extension(self):
        result = validate_filename("a" * 300 + ".pdf")
        self.assertTrue(result.endswith(".pdf"))
        self.assertLessEqual(len(result.encode("utf-8")), 255)


class ContentValidatorUnitTests(TestCase):
    """validate_file_content 直测：OOXML 分支与 CFB 分支的边界。"""

    def test_cfb_extensions_constant_matches_frozen_allowlist(self):
        self.assertEqual(CFB_EXTENSIONS, {"doc", "xls", "ppt"})
        self.assertEqual(SIGNATURE_DETECTED_EXTENSIONS, {"pdf", "docx", "xlsx", "pptx"})

    def test_cfb_partial_magic_rejected(self):
        upload = SimpleUploadedFile("x.doc", b"\xd0\xcf\x11\xe0" + b"\x00" * 100)
        with self.assertRaises(ValidationError):
            validate_file_content(upload, "doc")


class ChokePointWiringTests(TestCase):
    """收口装配事实：官方覆盖点指向本项目表单＋冻结配置值。"""

    def test_document_form_base_resolves_to_validated_form(self):
        self.assertIs(get_document_base_form(), ValidatedDocumentForm)

    def test_frozen_settings_facts(self):
        self.assertEqual(
            settings.WAGTAILDOCS_EXTENSIONS, ["doc", "docx", "pdf", "ppt", "pptx", "xls", "xlsx"]
        )
        self.assertEqual(settings.WAGTAILDOCS_MAX_UPLOAD_SIZE, 20 * 1024 * 1024)

    def test_document_model_clean_still_enforces_allowlist(self):
        """①扩展名约束由官方机制承担：构造越权扩展名的 Document 实例触发拒绝。"""
        document = Document(title="越权", file=SimpleUploadedFile("x.exe", b"MZ\x00\x00"))
        with self.assertRaises(ValidationError) as caught:
            document.full_clean(exclude=["uploaded_by_user"])
        self.assertIn("exe", str(caught.exception))
