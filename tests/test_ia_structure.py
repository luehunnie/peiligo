"""M2.1 结构实现测试：IA-01..IA-05 当前可验证部分 + 层级限制 + bootstrap 幂等。

断言清单引源 docs/INFORMATION_ARCHITECTURE.md §13（本步写入 IA-01..IA-05）：

- IA-01 板块中文名与 PRD §6 一字不差，旧站 3 个不一致命名未复入；
- IA-02 部门容器节点 URL GET 返回 404（等效不可达）；
- IA-03 容器不出现在 sitemap.xml（当前站点无 sitemap 发射器，守护空真；
  M2.2 §10 落地 sitemap 时按本类型排除并替换此守护）；
- IA-04 容器不出现在默认搜索结果（search_fields=[] 索引级排除，行为实测）；
- IA-05 板块 slug 命中 §4 表默认值 chronicle/events/materials/software/guide。

层级限制引源 IA §5 汇总表与补充约束（板块下不得跳过容器、容器下不得再建容器、
四层树深）；bootstrap 幂等/零假业务内容引源任务 GOAL 与 IA §1.3 建容器规则。
"""

from io import StringIO
from pathlib import Path

from departments.models import DepartmentContainerPage
from django.conf import settings
from django.core.management import call_command
from home.models import HomePage, SectionPage
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

# 冻结字面量（独立于 home.models.SECTIONS 书写，构成真实断言而非同义反复；
# 中文名冻结自 PRD §6 / IA §2，slug 为 IA §4.3 默认值）。
FROZEN_SECTIONS = [
    ("校园纪事", "chronicle"),
    ("校园活动", "events"),
    ("学习资料", "materials"),
    ("软件与工具", "software"),
    ("校园指南", "guide"),
]

# 旧站 3 个不一致命名（IA §2 / 旧站审计 R12）：弃用，不得复入任何代码或文案。
LEGACY_FORBIDDEN_NAMES = ["院内逸事", "软件资源", "学院指南"]

REPO_ROOT = Path(__file__).resolve().parents[1]

# IA-01「未复入」的源码级核对范围：实现代码与模板（tests 自身持有断言字面量，排除）。
SOURCE_SCAN_DIRS = ["home", "departments", "search", "src", "templates"]


class BootstrapSectionsTests(WagtailPageTestCase):
    """bootstrap_sections：五板块就位、安全幂等、复用既有 HomePage。"""

    def test_bootstrap_creates_five_published_sections_under_existing_home(self):
        home_before = Site.objects.get(is_default_site=True).root_page
        call_command("bootstrap_sections", stdout=StringIO())

        home = HomePage.objects.get(pk=home_before.pk)
        sections = list(SectionPage.objects.order_by("path"))
        self.assertEqual(len(sections), 5)
        self.assertEqual(
            [(s.title, s.slug) for s in sections],
            FROZEN_SECTIONS,
        )
        for section in sections:
            self.assertTrue(section.live, f"{section.slug} 应已发布")
            self.assertEqual(section.get_parent().pk, home.pk)
            # 站点相对路径断言：get_url_parts 不受 Site 数量影响（Page.url 在
            # 多站点缓存态下会退化为绝对 URL）。
            site_id, root_url, page_path = section.get_url_parts()
            self.assertIsNotNone(site_id)
            self.assertIsNotNone(root_url)
            self.assertEqual(page_path, f"/{section.slug}/")
        # 复用现有首页：不新建 HomePage、不重建站点（IA §1.1 全站唯一首页）。
        self.assertEqual(HomePage.objects.count(), 1)
        self.assertEqual(Site.objects.filter(is_default_site=True).count(), 1)

    def test_bootstrap_is_idempotent(self):
        call_command("bootstrap_sections", stdout=StringIO())
        pks_first = set(SectionPage.objects.values_list("pk", flat=True))

        out = StringIO()
        call_command("bootstrap_sections", stdout=out)

        pks_second = set(SectionPage.objects.values_list("pk", flat=True))
        self.assertEqual(len(pks_second), 5)
        self.assertEqual(pks_first, pks_second, "二次执行不得新建或删除板块页")
        self.assertIn("新建 0", out.getvalue())

    def test_bootstrap_zero_fake_business_content(self):
        """五板块之外零新建：无部门容器、无内容页（IA §1.3 建容器规则）。"""
        call_command("bootstrap_sections", stdout=StringIO())
        self.assertEqual(DepartmentContainerPage.objects.count(), 0)
        # 首页下子页恰为五板块（无任何其他结构或业务节点）。
        home = Site.objects.get(is_default_site=True).root_page
        self.assertEqual(home.get_children().count(), 5)


class SectionPagesTests(WagtailPageTestCase):
    """IA-01 / IA-05：冻结中文名与 slug；板块页前台 200。"""

    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_sections", stdout=StringIO())

    def test_ia01_section_titles_match_frozen_names(self):
        sections = {s.slug: s.title for s in SectionPage.objects.all()}
        self.assertEqual(sections, {slug: title for title, slug in FROZEN_SECTIONS})
        for title in sections.values():
            for legacy in LEGACY_FORBIDDEN_NAMES:
                self.assertNotIn(legacy, title)

    def test_ia05_slugs_and_urls(self):
        self.assertEqual(
            {s.slug for s in SectionPage.objects.all()},
            {"chronicle", "events", "materials", "software", "guide"},
        )
        for _, slug in FROZEN_SECTIONS:
            with self.subTest(slug=slug):
                response = self.client.get(f"/{slug}/")
                self.assertEqual(response.status_code, 200)

    def test_section_page_renders_title_with_structural_template(self):
        response = self.client.get("/chronicle/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/section_page.html")
        self.assertContains(response, "校园纪事")

    def test_homepage_still_renderable(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class HierarchyConstraintTests(WagtailPageTestCase):
    """IA §5 挂载约束汇总表：parent/subpage 类型白名单逐项核对。"""

    def test_homepage_only_under_root(self):
        self.assertCanCreateAt(Page, HomePage)
        self.assertCanNotCreateAt(HomePage, HomePage)
        self.assertCanNotCreateAt(SectionPage, HomePage)

    def test_section_only_under_homepage(self):
        self.assertCanCreateAt(HomePage, SectionPage)
        self.assertCanNotCreateAt(Page, SectionPage)
        self.assertCanNotCreateAt(SectionPage, SectionPage)
        self.assertCanNotCreateAt(DepartmentContainerPage, SectionPage)

    def test_container_only_under_section(self):
        self.assertCanCreateAt(SectionPage, DepartmentContainerPage)
        self.assertCanNotCreateAt(Page, DepartmentContainerPage)
        self.assertCanNotCreateAt(HomePage, DepartmentContainerPage)
        self.assertCanNotCreateAt(DepartmentContainerPage, DepartmentContainerPage)

    def test_container_subpages_are_five_content_types(self):
        """A3.1（CONTENT_MODEL §1.4）：容器子页白名单＝五类内容页。

        M2.1 时为空占位（test_container_allows_no_subpages_yet）；内容模型
        就位后终态＝五类，容器下不得再建容器/跳层。
        """
        from guides.models import GuidePage
        from notices.models import ArticlePage, NoticePage
        from resources.models import MaterialPage, SoftwareToolPage

        self.assertEqual(
            set(DepartmentContainerPage.creatable_subpage_models()),
            {NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage},
        )


class DepartmentContainerTests(WagtailPageTestCase):
    """IA-02 / IA-04 与容器结构语义（ADR-0004 决策 2 / IA §3）。"""

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

    def test_ia02_container_url_returns_404(self):
        _, _, page_path = self.container.get_url_parts()
        self.assertEqual(page_path, "/chronicle/jwc/")
        response = self.client.get("/chronicle/jwc/")  # 容器 URL 直达访问
        self.assertEqual(response.status_code, 404)

    def test_ia02_parent_section_still_200_with_container_present(self):
        response = self.client.get("/chronicle/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "校园纪事")

    def test_tree_shape_home_section_container(self):
        """Home→Section→Container 三层相邻，树径与 URL 同构（IA §1/§4 方案 A）。"""
        home = self.section.get_parent().specific
        self.assertEqual(home.__class__, HomePage)
        self.assertEqual(self.section.depth, home.depth + 1)
        self.assertEqual(self.container.depth, home.depth + 2)
        self.assertEqual(self.container.url_path, f"{home.url_path}chronicle/jwc/")

    def test_ia04_container_absent_from_default_search(self):
        """容器不得出现在默认搜索结果（IA-04）：按容器标题/slug 检索为空。

        M3.4（CONTENT_MODEL §21.1）：搜索对象域=五类内容页，容器经逐类型
        查询结构性排除（且容器 search_fields=[] 索引级排除仍在，双重缺席）。
        """
        for query in ("教务处", "教务处容器", "jwc"):
            with self.subTest(query=query):
                response = self.client.get("/search/", {"q": query})
                self.assertEqual(response.status_code, 200)
                result_pks = [page.pk for page in response.context["search_results"]]
                self.assertNotIn(self.container.pk, result_pks)

    def test_ia04_search_still_finds_normal_pages(self):
        """对照：内容页按标题可检索，证明搜索链路活着且容器缺席非偶然。

        M3.4（§21.1）：对象域=五类内容页——板块页等结构页同不入结果
        （此前对照主体为 SectionPage，随对象域冻结改为内容页）。
        """
        from tests.helpers import make_notice

        notice = make_notice(
            self.container, slug="n-searchable", title="开学典礼通知", publish=True
        )
        response = self.client.get("/search/", {"q": "开学典礼通知"})
        result_pks = [page.pk for page in response.context["search_results"]]
        self.assertIn(notice.pk, result_pks)
        self.assertNotIn(self.section.pk, result_pks)
        self.assertNotIn(self.container.pk, result_pks)

    def test_container_excluded_at_index_level(self):
        """索引级排除机制自证：容器清空 search_fields（含基类索引的 title）。"""
        self.assertEqual(DepartmentContainerPage.search_fields, [])

    def test_container_preview_disabled(self):
        """容器无前台页面可预览（serve 恒 404），后台预览关闭。"""
        self.assertEqual(DepartmentContainerPage.preview_modes, [])
        self.assertFalse(self.container.is_previewable())


class SitemapSurfaceTests(WagtailPageTestCase):
    """IA-03（M2.2 接管）：sitemap.xml 已接入且容器在模型级整类排除。

    M2.1 阶段为空真守护（无发射器且断言其不存在）；M2.2 引入
    wagtail.contrib.sitemaps 并以 DepartmentContainerPage.get_sitemap_urls→[]
    落实排除。行为级断言（容器在场时 /sitemap.xml 零容器 URL）见
    tests/test_ia_frontend.py::SitemapTests。
    """

    def test_ia03_sitemap_emitter_registered(self):
        self.assertIn("wagtail.contrib.sitemaps", settings.INSTALLED_APPS)
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)

    def test_ia03_container_excluded_at_model_level(self):
        self.assertEqual(DepartmentContainerPage().get_sitemap_urls(), [])


class LegacyNamingScanTests(WagtailPageTestCase):
    """IA-01「未复入」的源码级核对：实现代码与模板零旧站不一致命名。"""

    def test_legacy_section_names_absent_from_source(self):
        files = [
            path
            for directory in SOURCE_SCAN_DIRS
            for pattern in ("*.py", "*.html")
            for path in (REPO_ROOT / directory).rglob(pattern)
        ]
        self.assertGreater(len(files), 0)
        for path in files:
            content = path.read_text(encoding="utf-8")
            for legacy in LEGACY_FORBIDDEN_NAMES:
                self.assertNotIn(
                    legacy,
                    content,
                    msg=f"{legacy} 出现在 {path}（IA §2：旧站不一致命名禁止复入）",
                )
