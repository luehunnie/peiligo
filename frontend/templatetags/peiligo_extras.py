"""
前台展示辅助过滤器（Phase 8B 列表/搜索共享语言配套）。

零模型零迁移；三条过滤器均为纯展示层：

- ``section_short`` / ``section_tone``：板块身份的短名与 tone 类后缀，
  唯一事实源是 home.models.SECTIONS 的冻结 slug（SECTION_IDENTITY 冻结），
  与 static/css/peiligo.css 的 .ico-*/.tone-* 类一一对应；未识别 slug
  回落为中性展示（不猜色、不猜名）。
- ``highlight``：关键词高亮。安全管线＝先在原文上切片（finditer +
  re.escape 后的模式），再对每个片段（含命中片段）单独 ``escape()``，
  最后整体 ``mark_safe``——用户可控文本永不绕过 autoescape，等价于
  模板自动转义后再包一层无用户内容的 <mark> 标记。任何输入（含
  XSS payload）都不会产生未转义输出（回归见 tests/test_frontend_foundation.py）。
"""

from __future__ import annotations

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

register = template.Library()

# 与 SECTIONS 冻结 slug 对齐；tone 后缀对应 css 的 .tone-*/.ico-* 类。
SECTION_SHORT = {
    "chronicle": "纪事",
    "events": "活动",
    "materials": "资料",
    "software": "软件",
    "guide": "指南",
}

SECTION_TONE = {
    "chronicle": "jishi",
    "events": "huodong",
    "materials": "ziliao",
    "software": "gongju",
    "guide": "zhinan",
}


@register.filter
def section_short(slug: str) -> str:
    """板块 slug → 两字短名（chips/行内徽标用）；未识别 slug 原样回落。"""
    return SECTION_SHORT.get(slug, slug or "")


@register.filter
def section_tone(slug: str) -> str:
    """板块 slug → tone 类后缀（css .tone-<suffix>）；未识别返回空串。"""
    return SECTION_TONE.get(slug, "")


@register.filter
def highlight(value: object, query: str | None) -> SafeString | str:
    """把 *已转义安全的纯文本* 中命中的 query 片段包上 <mark>。

    管线（顺序即安全论证）：
    1. 原文 ``str(value)`` 上用 ``re.escape(query)`` 忽略大小写切片，
       模式本身不携带任何 HTML 语义；
    2. 每个片段（命中与非命中）独立 ``escape()``——标签字符一律实体化；
    3. 仅 <mark>（我们自己生成、不含用户内容）以 safe 片段插入；
    4. join 后整体 ``mark_safe``，产物中只含实体化文本与我们的标记。
    query 为空/非命中/None 时等价于单纯 ``escape()``。
    """
    text = str(value) if value is not None else ""
    if not query:
        return escape(text)

    pattern = re.compile(re.escape(str(query)), re.IGNORECASE)
    parts: list[str] = []
    last = 0
    for match in pattern.finditer(text):
        parts.append(escape(text[last : match.start()]))
        parts.append(f"<mark>{escape(match.group())}</mark>")
        last = match.end()
    parts.append(escape(text[last:]))
    return mark_safe("".join(parts))
