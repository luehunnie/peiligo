"""Phase 8B 前台共享基础测试：页头/页脚/板块身份/列表搜索语言/分页/高亮。

覆盖（evidence 报告 TESTS 清单对应）：

- 列表/搜索共享语言：板块页与 /search/ 渲染同一行式结果片段
  （r-row + 栏目徽标 + r-meta），软件板块呈 violet 身份；
- 板块身份：五冻结映射（SECTION_IDENTITY）仅经 CSS 类（tone-*/ico-*）
  与文字标签呈现，无任何数据库颜色字段（回归守门）；
- 分页：LIST_PAGE_SIZE、页码窗口（含 "…" 缺口）、非法页码宽容回退、
  翻页保留全部筛选参数；/search/ 与板块页同一实现；
- 关键词高亮：escape-safe 管线（XSS payload 不产生任何未转义输出，
  命中才有 <mark>；无命中/空 query 等价纯转义）；
- 栏目 chips：真实链接（保留其余参数），当前项 aria-current。
"""

from io import StringIO

from django.core.management import call_command
from django.template import Context, Template
from frontend.templatetags.peiligo_extras import section_short, section_tone
from home.models import SectionPage
from search.services import LIST_PAGE_SIZE, _page_links, paginate_entries
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import make_notice, make_software

# 与 tests/test_ia_frontend.py 同源的冻结五板块（独立性：本文件自行字面冻结）。
SECTION_SLUGS = ("chronicle", "events", "materials", "software", "guide")


class FoundationTestCase(WagtailPageTestCase):
    """公共基类：五板块 + 每板块一个部门容器（跨板块混合结果需要）。"""

    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_sections", stdout=StringIO())
        cls.sections = {slug: SectionPage.objects.get(slug=slug) for slug in SECTION_SLUGS}
        from departments.models import Department

        from tests.helpers import make_container

        cls.departments = {}
        cls.containers = {}
        for i, slug in enumerate(SECTION_SLUGS):
            department = Department.objects.create(name=f"部门{i}", slug=f"dept{i}")
            cls.departments[slug] = department
            cls.containers[slug] = make_container(cls.sections[slug], department)


class SharedListLanguageTests(FoundationTestCase):
    """板块页与 /search/ 共用同一行式结果语言（final-reference 列表页）。"""

    def test_section_page_renders_shared_row_language(self):
        notice = make_notice(
            self.containers["chronicle"], slug="row-1", title="共享行语言通知", publish=True
        )
        html = self.client.get("/chronicle/").content.decode()
        self.assertIn('<a class="r-row" href="/chronicle/dept0/row-1/">', html)
        self.assertIn('class="tag tone-jishi"', html)
        self.assertIn(">纪事</span>", html)
        # 板块身份图标块（coral 实心底 + 冻结线性图标）与定位文案同页。
        self.assertIn('class="sec-ico ico-jishi"', html)
        # 计数行（真实数量，非造假元数据）。
        self.assertIn("共 <strong>1</strong> 条", html)
        # 板块大搜索框提交回本板块（§9.1 板块页生效参数不变）。
        self.assertIn('action="/chronicle/"', html)
        self.assertEqual(notice.get_parent().get_parent().slug, "chronicle")

    def test_software_section_violet_identity_same_structure(self):
        """软件板块：violet 身份类；结构标记与纪事页完全同构（共享语言）。"""
        make_software(self.containers["software"], slug="sw-1", title="画图工具", publish=True)
        html = self.client.get("/software/").content.decode()
        self.assertIn('class="sec-ico ico-gongju"', html)
        self.assertIn('class="tag tone-gongju"', html)
        self.assertIn(">软件</span>", html)
        for marker in ('class="r-row"', 'class="results"', "共 <strong>1</strong> 条"):
            self.assertIn(marker, html)
        # 授权说明回落为行描述（旧卡回落链同序：summary→license_note→location）。
        self.assertIn("校园授权，免费使用", html)

    def test_section_identity_css_only_no_model_fields(self):
        """身份映射零模型字段守门：五类内容页/板块页无任何颜色字段。"""
        from guides.models import GuidePage
        from home.models import SectionPage as SP
        from notices.models import ArticlePage, NoticePage
        from resources.models import MaterialPage, SoftwareToolPage

        for model in (NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage, SP):
            field_names = {f.name for f in model._meta.get_fields()}
            for banned in ("theme_color", "color", "accent", "tone", "identity_color"):
                self.assertNotIn(banned, field_names, model.__name__)


class SearchSharedLanguageTests(FoundationTestCase):
    """/search/：行式结果、跨板块归属标注、计数行、栏目 chips。"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.notice = make_notice(
            cls.containers["chronicle"], slug="mix-n", title="混合检索共同词通知", publish=True
        )
        cls.tool = make_software(
            cls.containers["software"], slug="mix-sw", title="混合检索共同词工具", publish=True
        )

    def test_mixed_results_show_both_tones_and_section_labels(self):
        html = self.client.get("/search/", {"q": "共同词"}).content.decode()
        self.assertIn('class="tag tone-jishi"', html)
        self.assertIn('class="tag tone-gongju"', html)
        # 跨板块结果带栏目归属文字（颜色非唯一区分物）。
        self.assertIn("· 校园纪事", html)
        self.assertIn("· 软件与工具", html)
        # 计数行与两种身份的行并存。
        self.assertIn("找到 <strong>2</strong> 条", html)

    def test_type_chips_are_real_links_with_current_state(self):
        response = self.client.get("/search/", {"q": "共同词"})
        html = response.content.decode()
        self.assertIn('class="t-chip on"', html)
        self.assertIn('aria-current="true">全部</a>', html)
        for slug in SECTION_SLUGS:
            self.assertIn(f"section={slug}", html)
        # chips 为链接（非假按钮/非 JS 筛选）。
        self.assertNotIn('<button class="t-chip"', html)

    def test_section_chip_narrows_to_section(self):
        response = self.client.get("/search/", {"q": "共同词", "section": "software"})
        pks = [page.pk for page in response.context["search_results"]]
        self.assertEqual(pks, [self.tool.pk])


class PaginationTests(FoundationTestCase):
    """共享分页：常量、窗口、宽容回退、参数保留；两载体同一实现。"""

    def test_page_links_window_builder(self):
        class FakePaginator:
            def __init__(self, num_pages):
                self.num_pages = num_pages

        class FakePage:  # 只需 number 与 paginator.num_pages
            def __init__(self, number, num_pages):
                self.number = number
                self.paginator = FakePaginator(num_pages)

        self.assertEqual(_page_links(FakePage(1, 8)), [1, 2, "…", 8])
        self.assertEqual(_page_links(FakePage(4, 8)), [1, "…", 3, 4, 5, "…", 8])
        self.assertEqual(_page_links(FakePage(8, 8)), [1, "…", 7, 8])
        self.assertEqual(_page_links(FakePage(1, 1)), [1])

    def test_paginate_entries_graceful_fallbacks(self):
        entries = list(range(45))
        page, links = paginate_entries(entries, None)
        self.assertEqual(page.number, 1)
        page, _ = paginate_entries(entries, "abc")
        self.assertEqual(page.number, 1)  # 非整数 → 第 1 页（§21.3 同构宽容）
        page, _ = paginate_entries(entries, "999")
        self.assertEqual(page.number, 3)  # 越界 → 最后一页
        self.assertEqual(list(page.object_list), entries[40:45])
        self.assertEqual(LIST_PAGE_SIZE, 20)

    def test_search_pagination_pages_and_param_preservation(self):
        for i in range(25):
            make_notice(
                self.containers["chronicle"],
                slug=f"page-{i}",
                title=f"分页压测{i}pageword",
                publish=True,
            )
        first = self.client.get("/search/", {"q": "pageword"})
        html = first.content.decode()
        self.assertEqual(html.count('class="r-row"'), 20)
        self.assertIn("找到 <strong>25</strong> 条", html)
        self.assertIn('aria-current="page">1</span>', html)
        # 翻页链接保留 q 参数（querystring 剔除 page 之外全部保留）。
        self.assertIn('href="?q=pageword&amp;page=2"', html)
        self.assertIn("下一页 →", html)
        second = self.client.get("/search/", {"q": "pageword", "page": "2"})
        self.assertEqual(second.content.decode().count('class="r-row"'), 5)
        # 非法页码宽容回退：200 且有内容（不 404/不 500）。
        bad = self.client.get("/search/", {"q": "pageword", "page": "abc"})
        self.assertEqual(bad.status_code, 200)
        self.assertEqual(bad.content.decode().count('class="r-row"'), 20)
        far = self.client.get("/search/", {"q": "pageword", "page": "999"})
        self.assertEqual(far.status_code, 200)
        self.assertIn('aria-current="page">2</span>', far.content.decode())

    def test_section_page_pagination_shared_implementation(self):
        for i in range(21):
            make_notice(
                self.containers["chronicle"],
                slug=f"sec-page-{i}",
                title=f"板块分页{i}号",
                publish=True,
            )
        html = self.client.get("/chronicle/").content.decode()
        self.assertEqual(html.count('class="r-row"'), 20)
        self.assertIn("共 <strong>21</strong> 条", html)
        self.assertIn('href="?page=2"', html)
        second = self.client.get("/chronicle/", {"page": "2"})
        self.assertEqual(second.content.decode().count('class="r-row"'), 1)


class HighlightSafetyTests(FoundationTestCase):
    """关键词高亮 escape-safe 管线（XSS 回归）。"""

    @staticmethod
    def _render_highlight(text, q):
        return Template("{% load peiligo_extras %}{{ t|highlight:q }}").render(
            Context({"t": text, "q": q})
        )

    def test_highlight_filter_escapes_and_marks(self):
        render = self._render_highlight
        self.assertEqual(render("a<b>c", "<b>"), "a<mark>&lt;b&gt;</mark>c")
        self.assertEqual(render("AbC", "abc"), "<mark>AbC</mark>")  # 忽略大小写命中
        self.assertEqual(render("普通文本", "xyz"), "普通文本")  # 无命中＝纯转义
        self.assertEqual(render("<img src=x>", ""), "&lt;img src=x&gt;")  # 空 query
        self.assertEqual(str(section_tone("software")), "gongju")
        self.assertEqual(str(section_short("software")), "软件")

    def test_identity_filters_unknown_slug_fall_back_neutral(self):
        self.assertEqual(str(section_tone("bogus")), "")
        self.assertEqual(str(section_short("bogus")), "bogus")
        self.assertEqual(str(section_tone("")), "")
        self.assertEqual(str(section_short("")), "")

    def test_xss_payload_in_query_never_produces_raw_markup(self):
        """payload 作搜索词：任何表面不出现未转义标签/属性（自动转义+高亮管线）。"""
        for payload in (
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            '"><svg onload=alert(1)>',
        ):
            with self.subTest(payload=payload):
                response = self.client.get("/search/", {"q": payload})
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertNotIn("<script>alert", html)
                self.assertNotIn("<img src=x", html)
                self.assertNotIn("<svg onload", html)
                # echo 位（s-sum / 空态）为实体化文本。
                self.assertIn("&lt;script&gt;", html) if payload.startswith("<script") else None

    def test_highlighted_title_from_html_like_content_stays_escaped(self):
        """内容含 HTML 字面文本时命中渲染：mark 只包实体化文本，零原始标签。"""
        make_notice(
            self.containers["chronicle"],
            slug="htmlish",
            title="使用<b>加粗</b>写法指南",
            publish=True,
        )
        response = self.client.get("/search/", {"q": "<b>加粗</b>"})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("使用<b>加粗</b>写法", html)  # 原始标签永不入输出
        self.assertIn("<mark>&lt;b&gt;加粗&lt;/b&gt;</mark>", html)

    def test_result_row_has_no_inline_event_handlers(self):
        """行式片段零 inline 事件处理器（本阶段不清理既有债务、但不得新增）。"""
        make_notice(
            self.containers["chronicle"], slug="inline-x", title="内联事件守门通知", publish=True
        )
        html = self.client.get("/search/", {"q": "内联事件守门"}).content.decode()
        for bad in ("onclick=", "onload=", "onerror=", "javascript:"):
            self.assertNotIn(bad, html)
