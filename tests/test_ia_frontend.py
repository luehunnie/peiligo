"""M2.2 前台 IA 实现测试：IA-06..IA-14 当前可验证部分 + 基础无障碍语义。

断言清单引源 docs/INFORMATION_ARCHITECTURE.md §13（M2.2 增补 IA-06..14；
本步覆盖其中不依赖 M3 模型的部分）：

- IA-06（Phase 8B 修订：人类冻结决策①）页头=校徽+字标+全局搜索，七项
  文字导航移除；板块默认列表无容器条目、全站不链接容器；
- IA-07 面包屑：首页无、板块页=首页>板块、当前页纯文本、容器段永不出现；
  Phase 8B 起 /search/ 为中性搜索壳、无面包屑；
- IA-10 首页/板块页默认可收录（无 noindex meta）且进入 sitemap；
- IA-12 /search/（含无参数态）与板块 query 态输出 noindex+canonical 去参 URL，
  query 态不入 sitemap；
- IA-13 首页五板块入口网格：恰五项、冻结顺序（§2 #1–#5）、链接均 200；
- IA-14 全空态（板块无参数态）与筛选无匹配态（搜索无结果）文案与动作区分；
- IA-03（行为级）容器在场时 /sitemap.xml 零容器 URL。

明确延后（依赖 M3，当前不可验证、不伪造）：IA-08/IA-09（筛选态标题、
单篇 noindex 字段）、IA-11 五参数规格（MB10）、IA-13 层 1–3 数据区、
IA-14 载入中/出错态（纯 SSR 无客户端加载，ADR-0002）。

无障碍语义（PRD §13 / IA §6.1）：html lang、跳转主内容链接、landmark
（header/nav/main/footer）、每页唯一 h1、当前导航项 aria-current。

页头品牌区校徽（Phase 5 增补）：学校归属锚点走站内 static 资产、
纯装饰 alt=""，品牌字标仍在、导航七类与无 hamburger 不变量随测。
"""

import re
from io import StringIO
from pathlib import Path

from departments.models import DepartmentContainerPage
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from home.models import SectionPage
from wagtail.test.utils import WagtailPageTestCase

# 冻结字面量（独立于 home.models.SECTIONS / 模板书写，构成真实断言而非同义反复；
# IA §2 / §4.3：中文名=PRD §6 一字不差，slug 为默认值）。
FROZEN_SECTION_ORDER = [
    ("校园纪事", "chronicle"),
    ("校园活动", "events"),
    ("学习资料", "materials"),
    ("软件与工具", "software"),
    ("校园指南", "guide"),
]

# Phase 8B（人类冻结决策①）：七项文字导航移除——页头不得再出现这些
# 导航条目（可达性改由首页板块卡/面包屑/列表筛选/页脚承担）。
FORBIDDEN_NAV_LABELS = ["首页", *(title for title, _ in FROZEN_SECTION_ORDER), "站内搜索"]

# 全部会被断言的前台表面（404 表面单独构造）。
PUBLIC_SURFACES = ["/", "/chronicle/", "/guide/", "/search/"]


class FrontendIATestCase(WagtailPageTestCase):
    """公共基类：五板块就位 + 在校园纪事下挂一个已发布容器。

    容器在场使"排除类"断言为真实行为级验证（容器存在却零出现），
    而非因无数据而空真（与 M2.1 test_ia_structure 同款做法）。
    """

    @classmethod
    def setUpTestData(cls):
        from departments.models import Department

        call_command("bootstrap_sections", stdout=StringIO())
        cls.section = SectionPage.objects.get(slug="chronicle")
        # A3.1（CONTENT_MODEL §4）：容器必填绑定 Department。
        cls.department = Department.objects.create(name="教务处", slug="jwc")
        cls.container = DepartmentContainerPage(
            title="教务处容器", slug="jwc", department=cls.department
        )
        cls.section.add_child(instance=cls.container)
        cls.container.save_revision().publish()

    # -- 小工具：从响应中截取命名区域（nav/breadcrumb）内层标记 ----------
    @staticmethod
    def _extract_block(html: str, aria_label: str) -> str:
        match = re.search(rf'<[^>]*aria-label="{aria_label}"[^>]*>(.*?)</nav>', html, re.DOTALL)
        assert match, f"未找到 aria-label={aria_label!r} 的区块"
        return match.group(1)

    @staticmethod
    def _extract_header_block(html: str) -> str:
        match = re.search(r"<header.*?</header>", html, re.DOTALL)
        assert match, "未找到 <header> 区块"
        return match.group(0)


class GlobalNavigationTests(FrontendIATestCase):
    """IA-06（Phase 8B 页头口径）：品牌+全局搜索、七项导航移除、容器零出现。"""

    def test_header_has_brand_and_global_search_no_nav_on_all_surfaces(self):
        """全部公开表面：页头含品牌链接与全局搜索 GET 表单（action=/search/
        name=q），不再有「全局导航」nav，旧七项导航条目零出现。"""
        for url in PUBLIC_SURFACES:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                header = self._extract_header_block(html)
                self.assertIn('class="brand" href="/"', header)
                self.assertIn('class="wordmark"', header)
                self.assertIn('action="/search/"', header)
                self.assertIn('name="q"', header)
                self.assertNotIn("全局导航", html)
                nav = self._extract_header_block(html)
                labels_present = [label for label in FORBIDDEN_NAV_LABELS if f">{label}</a>" in nav]
                self.assertEqual(labels_present, [])

    def test_header_search_preserves_current_query(self):
        """页头搜索回显当前搜索词（q 参数 → input value），刷新/改词可用。"""
        response = self.client.get("/search/", {"q": "开学典礼"})
        html = response.content.decode()
        self.assertIn('value="开学典礼"', html)

    def test_ia06_container_never_linked_on_any_surface(self):
        """全站模板不生成任何指向 /<板块>/<部门>/ 的链接（§6.2 导航行）。"""
        urls = PUBLIC_SURFACES + ["/no-such-page/"]  # 末项为 404 表面
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, (200, 404))
                self.assertNotContains(
                    response, "/chronicle/jwc/", status_code=response.status_code
                )

    def test_ia06_section_default_list_has_no_container_entry(self):  # noqa: D102（IA-06 沿用）
        """板块默认列表（当前为全空态）不出现容器条目/容器标题（§6.2 列表行）。"""
        response = self.client.get("/chronicle/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.container.title)


class HeaderBrandLogoTests(FrontendIATestCase):
    """页头品牌区校徽（Phase 5 增补，IA §6.1）：归属锚点不破坏页头不变量。

    校徽为小尺寸视觉归属锚点（纯装饰 alt=""，品牌 link accessible name
    仍为 site_brand）；资产入库仓库 static，禁热链与 Desktop 绝对路径，
    被替换的旧背景版资产零残留；加校徽后导航仍固定七类，不新增
    hamburger/隐藏入口。
    """

    # 与模板 {% static 'img/peiligo-school-logo.png' %} 对应的渲染路径
    # （STATIC_URL = "/static/"，settings/base.py §静态资源）。
    BRAND_LOGO_STATIC_PATH = "/static/img/peiligo-school-logo.png"

    @staticmethod
    def _extract_header(html: str) -> str:
        match = re.search(r"<header.*?</header>", html, re.DOTALL)
        assert match, "未找到 <header> 区块"
        return match.group(0)

    def test_brand_keeps_peiligo_wordmark_and_decorative_logo(self):
        """品牌 link 仍含 Peiligo 字标；校徽走 Django static 路径且 alt=""
        （读屏 accessible name 不因校徽重复或混乱）。"""
        for url in PUBLIC_SURFACES:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                header = self._extract_header(response.content.decode())
                brand = re.search(r'<a class="brand"[^>]*>.*?</a>', header, re.DOTALL)
                self.assertIsNotNone(brand)
                # Phase 8B 字标形态：wordmark span（含 coral 句点装饰）。
                self.assertRegex(brand.group(0), r'<span class="wordmark">\s*Peiligo')
                self.assertIn('class="wm-dot"', brand.group(0))
                self.assertIn(f'src="{self.BRAND_LOGO_STATIC_PATH}"', brand.group(0))
                self.assertRegex(brand.group(0), r'<img class="brand-logo"[^>]*alt=""')

    def test_logo_asset_ships_in_repo_static(self):
        """Logo 资产实际存在于仓库 static 目录且可被 static 系统定位（非外链）。"""
        found = finders.find("img/peiligo-school-logo.png")
        self.assertIsNotNone(found)
        expected = settings.BASE_DIR / "static" / "img" / "peiligo-school-logo.png"
        self.assertEqual(Path(found), expected)

    def test_superseded_logo_assets_absent(self):
        """被替换的旧背景版 Logo 零残留：页头不引用 images.jpeg /
        peiligo-school-logo.jpeg，static/img 无 jpeg 文件遗留。"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("images.jpeg", html)
        self.assertNotIn("peiligo-school-logo.jpeg", html)
        img_dir = settings.BASE_DIR / "static" / "img"
        self.assertEqual(list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.jpg")), [])

    def test_logo_not_hotlinked_and_no_desktop_path(self):
        """Logo src 为站内 /static/ 相对路径；页头无远程热链与绝对路径依赖。"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        header = self._extract_header(response.content.decode())
        logo_src = re.search(r'<img class="brand-logo"[^>]*src="([^"]+)"', header)
        self.assertIsNotNone(logo_src)
        self.assertTrue(logo_src.group(1).startswith("/static/"))
        self.assertFalse(logo_src.group(1).startswith(("http://", "https://")))
        self.assertNotIn("/Users/", header)
        self.assertNotIn("Desktop", header)

    def test_navigation_invariants_with_brand_logo(self):
        """Phase 8B 页头不变量：无导航列表、无 hamburger/切换按钮等新增入口
        （可达性改由首页板块卡/面包屑/列表筛选/页脚承担——人类冻结决策①）。"""
        for url in PUBLIC_SURFACES:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                header = self._extract_header(response.content.decode())
                self.assertNotIn("全局导航", header)
                self.assertNotIn("<nav", header)
                header_lower = header.lower()
                for forbidden in ("hamburger", "nav-toggle", "menu-toggle", "<button"):
                    self.assertNotIn(forbidden, header_lower)


class BreadcrumbTests(FrontendIATestCase):
    """IA-07：面包屑按 §6.3——首页无、板块=首页>板块、当前页纯文本、容器永不出现。"""

    def test_ia07_homepage_has_no_breadcrumb(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'aria-label="面包屑"')

    def test_ia07_section_breadcrumb_is_home_link_then_plain_title(self):
        response = self.client.get("/chronicle/")
        self.assertEqual(response.status_code, 200)
        crumb = self._extract_block(response.content.decode(), "面包屑")
        # 除最后一段（当前页，纯文本）外每段可点且指向 200 URL（§6.3）。
        links = re.findall(r'<a href="([^"]+)">', crumb)
        self.assertEqual(links, ["/"])
        self.assertIn("校园纪事", crumb)
        self.assertNotIn("教务处", crumb)  # 容器段永不出现（链接与纯文本均不出现）
        # 当前段不是链接、以 aria-current 标注。
        current = re.search(r'<span aria-current="page">([^<]+)</span>', crumb)
        self.assertIsNotNone(current)
        self.assertEqual(current.group(1), "校园纪事")

    def test_ia07_breadcrumb_links_resolve_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)  # 面包屑唯一链接目标即首页

    def test_ia07_search_page_has_no_breadcrumb(self):
        """Phase 8B（final-reference）：/search/ 为中性搜索壳，无面包屑
        （壳内大搜索框即页面身份；IA-07 载体清单相应修订）。"""
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'aria-label="面包屑"')


class RobotsMetaTests(FrontendIATestCase):
    """IA-10（默认可收录）与 IA-12（query 态/搜索页 noindex+canonical）。"""

    def test_ia10_home_and_sections_default_indexable(self):
        for url in ["/", *[f"/{slug}/" for _, slug in FROZEN_SECTION_ORDER]]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, '<meta name="robots"')

    def test_ia12_search_page_noindex_including_parameterless_state(self):
        for url in ("/search/", "/search/?query=校园"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<meta name="robots" content="noindex">')
                self.assertContains(
                    response, '<link rel="canonical" href="http://testserver/search/">'
                )

    def test_ia12_section_query_state_noindex_with_clean_canonical(self):
        response = self.client.get("/chronicle/", {"dept": "jwc"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="robots" content="noindex">')
        # canonical 指向去除全部 query 参数的基础 URL（§10.1）。
        self.assertContains(response, '<link rel="canonical" href="http://testserver/chronicle/">')

    def test_ia12_section_without_query_has_no_canonical(self):
        response = self.client.get("/chronicle/")
        self.assertNotContains(response, 'rel="canonical"')


class SitemapTests(FrontendIATestCase):
    """IA-03（行为级）+ IA-10：sitemap 仅含 200 页面树节点（首页+五板块）。"""

    def test_ia03_ia10_sitemap_contains_home_and_sections_only(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        locs = re.findall(r"<loc>([^<]+)</loc>", response.content.decode())
        paths = [re.sub(r"^https?://[^/]+", "", loc) for loc in locs]
        self.assertEqual(
            sorted(paths),
            sorted(["/", *[f"/{slug}/" for _, slug in FROZEN_SECTION_ORDER]]),
        )

    def test_ia03_container_absent_from_sitemap_when_live(self):
        response = self.client.get("/sitemap.xml")
        self.assertContains(response, "<loc>", count=6)
        self.assertNotContains(response, "/chronicle/jwc/")

    def test_ia12_sitemap_has_no_query_state_urls(self):
        """query 状态页不在页面树，sitemap 贡献位仅 200 基础 URL（§10.1）。"""
        response = self.client.get("/sitemap.xml")
        locs = re.findall(r"<loc>([^<]+)</loc>", response.content.decode())
        self.assertEqual(len(locs), 6)
        self.assertTrue(all("?" not in loc and "&" not in loc for loc in locs))


class HomePageEntryGridTests(FrontendIATestCase):
    """IA-13（Phase 8C 定稿载体）：五板块入口＝五分类导航条，恰五项、
    冻结顺序、SECTION_IDENTITY 身份类、链接 200。"""

    def test_ia13_category_nav_has_five_entries_in_frozen_order(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/home_page.html")
        html = response.content.decode()
        nav = re.search(r'<nav class="cats"[^>]*>(.*?)</nav>', html, re.DOTALL)
        self.assertIsNotNone(nav)
        hrefs = re.findall(r'<a class="cat[^"]*" href="([^"]+)">', nav.group(1))
        self.assertEqual(hrefs, [f"/{slug}/" for _, slug in FROZEN_SECTION_ORDER])
        for title, _ in FROZEN_SECTION_ORDER:
            self.assertIn(title, nav.group(1))

    def test_ia13_category_nav_carries_identity_classes(self):
        """冻结身份映射（SECTION_IDENTITY）：cat-<tone> 恰各一次，颜色不作
        唯一区分物（文字标签恒在）。"""
        # 冻结 tone 映射（§5.2 SECTION_IDENTITY；peiligo_extras.section_tone 同源）。
        cat_tone_by_slug = {
            "chronicle": "jishi",
            "events": "huodong",
            "materials": "ziliao",
            "software": "gongju",
            "guide": "zhinan",
        }
        html = self.client.get("/").content.decode()
        nav = re.search(r'<nav class="cats"[^>]*>(.*?)</nav>', html, re.DOTALL)
        self.assertIsNotNone(nav)
        for _, slug in FROZEN_SECTION_ORDER:
            with self.subTest(slug=slug):
                self.assertEqual(nav.group(1).count(f"cat-{cat_tone_by_slug[slug]}"), 1)

    def test_ia13_grid_links_all_resolve_200(self):
        for _, slug in FROZEN_SECTION_ORDER:
            with self.subTest(slug=slug):
                self.assertEqual(self.client.get(f"/{slug}/").status_code, 200)

    def test_homepage_h1_is_chinese_title(self):
        """脚手架种子标题已中文化（M2.2 迁移）；Phase 8C 视觉主位由 Hero
        大题承担，页面 h1 保留中文标题、视觉隐藏（全页恒一个 h1）。"""
        html = self.client.get("/").content.decode()
        self.assertIn('<h1 class="visually-hidden">首页</h1>', html)
        self.assertEqual(html.count("<h1"), 1)


class EmptyStateTests(FrontendIATestCase):
    """IA-14（当前可验证部分）：全空态与筛选无匹配态的文案及动作区分。"""

    def test_ia14_section_all_empty_state_with_guidance(self):
        response = self.client.get("/chronicle/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "本板块暂无内容")
        self.assertContains(response, "返回首页")
        # 引导覆盖其余四个板块（五板块减当前）。
        for title, slug in FROZEN_SECTION_ORDER:
            with self.subTest(slug=slug):
                if slug == "chronicle":
                    self.assertNotContains(response, f'<a href="/{slug}/">{title}</a>')
                else:
                    self.assertContains(response, f'<a href="/{slug}/">{title}</a>')

    def test_ia14_search_no_match_state_distinct_from_all_empty(self):
        """M3.4：q 参数生效＋已选条件回显（IA §11）；文案动作与"全空"态区分。"""
        response = self.client.get("/search/", {"q": "绝不存在的关键词zzz"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "没有符合当前条件的内容")
        self.assertContains(response, "清除搜索条件")
        self.assertContains(response, 'href="/search/"')
        self.assertContains(response, "关键词「绝不存在的关键词zzz」")
        self.assertNotContains(response, "本板块暂无内容")

    def test_search_still_finds_content_pages(self):
        """对照：搜索链路活着（内容页按标题可检索）；结构页/容器不入结果
        （M3.4 §21.1 对象域=五类内容页；容器缺席见 M2.1 IA-04 测试）。"""
        from tests.helpers import make_notice

        notice = make_notice(self.container, slug="n-findable", title="开学典礼通知", publish=True)
        response = self.client.get("/search/", {"q": "开学典礼通知"})
        self.assertEqual(response.status_code, 200)
        result_pks = [page.pk for page in response.context["search_results"]]
        self.assertIn(notice.pk, result_pks)
        self.assertNotIn(self.section.pk, result_pks)
        self.assertNotIn(self.container.pk, result_pks)


class Generic404Tests(FrontendIATestCase):
    """通用 404 页（IA §11 末条）：搜索+五板块入口，不做部门化引导。"""

    def test_unknown_path_renders_generic_404_template(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "页面不存在", status_code=404)
        self.assertContains(response, "站内搜索", status_code=404)
        for title, _ in FROZEN_SECTION_ORDER:
            self.assertContains(response, title, status_code=404)

    def test_container_404_uses_same_generic_page_without_department_hint(self):
        """容器 URL 的 404 同用通用页，文案不含部门段引导（§11 末条）。"""
        response = self.client.get("/chronicle/jwc/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertNotContains(response, self.container.title, status_code=404)
        self.assertContains(response, "站内搜索", status_code=404)


class FooterToolEntriesTests(FrontendIATestCase):
    """页脚关于/反馈工具入口（IA §6.1）：每页在、反馈链接带标题与页面地址（PRD §8）。"""

    def test_footer_about_and_feedback_on_all_surfaces(self):
        for url in PUBLIC_SURFACES + ["/no-such-page/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, (200, 404))
                self.assertContains(response, "关于", status_code=response.status_code)
                self.assertContains(response, "反馈", status_code=response.status_code)
                self.assertContains(
                    response,
                    f"mailto:{settings.FEEDBACK_EMAIL}",
                    status_code=response.status_code,
                )

    def test_feedback_mailto_carries_page_title_and_url(self):
        """邮件链接自动带上内容标题与页面地址（PRD §8 / §6.1 反馈条）。"""
        from urllib.parse import quote

        response = self.client.get("/chronicle/")
        mailto = re.search(r'href="(mailto:[^"]+)"', response.content.decode())
        self.assertIsNotNone(mailto)
        # Django urlencode 模板过滤器的默认 safe 集（含 "/"，与 quote() 一致）。
        self.assertIn(f"subject={quote('校园纪事')}", mailto.group(1))
        self.assertIn(quote("http://testserver/chronicle/"), mailto.group(1))


class AccessibilitySemanticsTests(FrontendIATestCase):
    """基础无障碍语义（PRD §13 / ADR-0002 纯 SSR 输出）。"""

    def test_html_lang_and_skip_link_and_landmarks(self):
        for url in PUBLIC_SURFACES:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertIn('<html lang="zh-hans">', html)
                # 跳转链接是 body 内首个链接，且目标锚点真实存在。
                self.assertIn('class="skip-link" href="#main-content"', html)
                self.assertIn('<main id="main-content"', html)
                for landmark in ("<header", "<footer"):
                    self.assertIn(landmark, html)
                # Phase 8B：页头全局搜索表单（role=search + 站内搜索命名）。
                self.assertIn('role="search"', html)
                self.assertIn('aria-label="站内搜索"', html)

    def test_exactly_one_h1_per_surface(self):
        for url in PUBLIC_SURFACES:
            with self.subTest(url=url):
                response = self.client.get(url)
                html = response.content.decode()
                self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)

    def test_search_form_has_accessible_name(self):
        """M3.4：搜索框参数名 q（IA §9.1）；Phase 8B 定稿壳无可见 label，
        可访问命名经 aria-label 承担（大搜索框 input）。"""
        response = self.client.get("/search/")
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'id="id_q"')
        self.assertContains(response, 'aria-label="搜索词"')
