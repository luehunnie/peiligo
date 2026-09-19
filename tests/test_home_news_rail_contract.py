"""校园快讯滚动轨响应式合同（2026-09-19 六卡改版）。

断言面＝静态资产合同（CSS/模板文本级；运行时组稿语义由
test_home_data_areas.CampusNewsTests 覆盖，视觉行为由浏览器验收截图
覆盖）：全断点原生横向滚动＋scroll-snap（仅该轨滚动，文档不横向溢出）；
卡宽三档阶梯——≤760 一卡＋露边（82%）、761–1279 两卡＋peek、≥1280
三卡＋peek——peek 恒为正，轨道永不整行摊开；轨道＝可聚焦滚动区
（region 语义＋tabindex）；跨年条目日期带年份。
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

CSS_PATH = Path("static/css/peiligo.css")
TEMPLATE_PATH = Path("home/templates/home/home_page.html")


def _rule_block(css: str, selector: str) -> str:
    """取顶层规则体（选择器后第一对花括号；本合同涉及的规则均无嵌套）。"""
    match = re.search(re.escape(selector) + r"\s*\{([^{}]*)\}", css)
    assert match is not None, f"rule not found: {selector}"
    return match.group(1)


def _media_block(css: str, query: str) -> str:
    """取整段 @media 块体（花括号配平扫描；块内允许多层嵌套）。"""
    start = css.index(query)
    open_brace = css.index("{", start)
    depth, i = 1, open_brace + 1
    while depth:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    return css[open_brace + 1 : i - 1]


class NewsRailScrollContractTests(SimpleTestCase):
    """滚动轨 CSS 合同：原生滚动、snap、滚动条隐藏、贴边与 peek 阶梯。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_rail_is_native_horizontal_scroller_at_all_widths(self):
        body = _rule_block(self.css, ".news-rail")
        self.assertIn("overflow-x: auto", body)
        self.assertIn("flex-wrap: nowrap", body)
        self.assertIn("scroll-snap-type: x mandatory", body)
        self.assertIn("scrollbar-width: none", body)

    def test_rail_never_uses_grid_layout(self):
        """旧三等分网格退场：轨道不再出现任何 grid 布局声明。"""
        self.assertNotIn("grid-template-columns", _rule_block(self.css, ".news-rail"))

    def test_base_card_is_one_up_with_peek(self):
        """≤760 基础层：单卡 82% 宽＋18% 露边，snap 对齐卡首。"""
        body = _rule_block(self.css, ".news-card")
        self.assertIn("width: 82%", body)
        self.assertIn("scroll-snap-align: start", body)

    def test_tablet_tier_is_two_cards_plus_peek(self):
        tier = _media_block(self.css, "@media (min-width: 761px)")
        self.assertIn("flex-basis: calc((100% - 18px - 44px) / 2)", tier)
        self.assertIn("margin-inline: 0", tier)  # ≥761 收回贴边（与栅格对齐）

    def test_desktop_tier_is_three_cards_plus_peek(self):
        tier = _media_block(self.css, "@media (min-width: 1280px)")
        self.assertIn("flex-basis: calc((100% - 36px - 48px) / 3)", tier)

    def test_peek_is_strictly_positive_in_every_tier(self):
        """peek 恒为正：三档卡宽算式都扣除一个正的 peek 项（下一张卡必露
        一角，轨道永不整行摊开——本合同的人机意图锚点）。"""
        base = _rule_block(self.css, ".news-card")
        tablet = _media_block(self.css, "@media (min-width: 761px)")
        desktop = _media_block(self.css, "@media (min-width: 1280px)")
        self.assertIn("82%", base)
        self.assertRegex(tablet, r"calc\(\(100% - 18px - [1-9]\d*px\) / 2\)")
        self.assertRegex(desktop, r"calc\(\(100% - 36px - [1-9]\d*px\) / 3\)")

    def test_reduced_motion_block_untouched(self):
        """reduced-motion 全局降级仍在（滚动为用户手势驱动，无需额外豁免）。"""
        tier = _media_block(self.css, "@media (prefers-reduced-motion: reduce)")
        self.assertIn("transition-duration: 0.01ms", tier)


class NewsRailTemplateContractTests(SimpleTestCase):
    """模板合同：可聚焦滚动区语义＋跨年日期带年份。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_rail_is_focusable_region_with_accessible_name(self):
        self.assertIn(
            'role="region" aria-label="校园快讯列表" tabindex="0"', self.template
        )

    def test_noncurrent_year_renders_full_date(self):
        self.assertIn('{% now "Y" as news_current_year %}', self.template)
        self.assertIn("{% if item.date|date:'Y' != news_current_year %}", self.template)
