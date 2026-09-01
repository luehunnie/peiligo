"""F-03 · 外部链接校验与展示规范化（SECURITY_BASELINE §10-7 / CM §11.4）。

逐条对应 SB §10-7 展示与比对统一规则：strip 后校验（1）／scheme+host
小写化比对与展示（2）／URLValidator 格式校验（3）／缺协议拒绝且不静默
补全（4）／user:pass 凭据段（userinfo）拒绝（5）／相对与 scheme 相对
形式拒绝（6）／scheme 白名单收窄 http/https（7）。

挂接：字段层＝4 处 URLField 与外链块 URLBlock 的 validators（运行时
校验不改变迁移状态）；输出层＝确认页与继续访问端点对目标二次校验
（防库内历史脏数据，SB §10-7 校验位置条）。
"""

from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

ALLOWED_URL_SCHEMES = ("http", "https")

MSG_MISSING_SCHEME = "链接缺少协议（如 https://），请补全后重填。"
MSG_SCHEME_NOT_ALLOWED = "仅支持 http:// 或 https:// 开头的链接。"
MSG_USERINFO = "链接不能包含用户名/密码凭据段（@），请改用不带凭据的地址。"
MSG_WHITESPACE = "链接中不能包含空格或换行。"

_url_validator = URLValidator(
    schemes=list(ALLOWED_URL_SCHEMES), message="链接格式不正确，请检查后重填。"
)


def validate_external_url(value: str) -> str:
    """SB §10-7 全规则校验；返回 strip 后的候选值，非法即 ValidationError。"""
    candidate = (value or "").strip()
    if not candidate:
        return candidate  # 空值合法性（blank）由字段声明承担
    if any(ch.isspace() for ch in candidate):
        raise ValidationError(MSG_WHITESPACE)
    if "://" not in candidate:
        # 一并覆盖：缺协议（4）、//host scheme 相对（6）、mailto:/javascript:
        # 等非白名单 scheme 形态（7）。
        raise ValidationError(MSG_MISSING_SCHEME)
    if candidate.split("://", 1)[0].lower() not in ALLOWED_URL_SCHEMES:
        raise ValidationError(MSG_SCHEME_NOT_ALLOWED)
    parsed = urlparse(candidate)
    if parsed.username or parsed.password:
        raise ValidationError(MSG_USERINFO)
    _url_validator(candidate)
    return candidate


def display_external_url(value: str) -> str:
    """SB §10-7 规则 2：scheme 与 host 小写化的展示形态（路径/查询保留）。"""
    parsed = urlparse((value or "").strip())
    if not parsed.netloc:
        return value
    return parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower()).geturl()


def external_url_domain(value: str) -> str:
    """确认页四要素之「目标域名」：host 小写、剥离端口。"""
    return urlparse((value or "").strip()).hostname or ""
