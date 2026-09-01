"""F-06 SEO 三项缺口回归（IA §10）。

断言面：robots.txt（自定义视图，text/plain；管理面/外链确认页 Disallow，
/search/ 刻意不 Disallow——noindex 是收录语义，robots 禁抓反使 meta 读
不到）；逐内容页 noindex 开关（五类内容页同构字段，缺省 False＝默认可
收录：前台 meta noindex ＋ sitemap.xml 双消费位；首页/板块/容器/自定义
视图无此字段，模板属性查找静默为假）；外链确认页整页恒 noindex（F-03
独立位点，不在本字段管辖）。
"""

from django.test import Client
from guides.models import GuidePage
from notices.models import ArticlePage, NoticePage
from resources.models import MaterialPage, SoftwareToolPage

from tests.test_ia_frontend import FrontendIATestCase

FIVE_CONTENT_MODELS = (NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage)


class RobotsTxtTests(FrontendIATestCase):
    """robots.txt：路由/内容类型/指令面。"""

    def setUp(self):
        self.client = Client()
        self.response = self.client.get("/robots.txt")
        self.body = self.response.content.decode()

    def test_route_and_content_type(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertIn("text/plain", self.response["Content-Type"])

    def test_disallow_admin_and_link_confirm(self):
        self.assertIn("User-agent: *", self.body)
        self.assertIn("Disallow: /django-admin/", self.body)
        self.assertIn("Disallow: /admin/", self.body)
        self.assertIn("Disallow: /link-confirm/", self.body)

    def test_search_not_disallowed(self):
        """noindex ≠ robots Disallow：/search/ 必须可抓取才能读到 meta。"""
        self.assertNotIn("Disallow: /search", self.body)

    def test_sitemap_absolute_url(self):
        self.assertIn("Sitemap: http://testserver/sitemap.xml", self.body)


class NoindexFieldWiringTests(FrontendIATestCase):
    """逐内容页 noindex：五类内容页同构接线＋冻结缺省。"""

    def test_field_present_on_all_five_content_models(self):
        for model in FIVE_CONTENT_MODELS:
            field = model._meta.get_field("noindex")
            self.assertIsNotNone(field, model.__name__)
            self.assertFalse(field.default, f"{model.__name__} 缺省必须可收录（IA §10 #7）")

    def test_wiring_facts(self):
        """接线事实：字段属 SeoControlMixin；promote 面板尾挂 seo_panels
        （模型类声明式拼接——官方 promote_panels 含未绑定 PanelPlaceholder，
        不可按 varname 展开，改断言 seo_panels 实例在列）。"""
        from peiligo.seo import SeoControlMixin

        for model in FIVE_CONTENT_MODELS:
            self.assertTrue(
                issubclass(model, SeoControlMixin), f"{model.__name__} 未挂 SeoControlMixin"
            )
            for panel in SeoControlMixin.seo_panels:
                self.assertIn(panel, model.promote_panels, f"{model.__name__} promote 面板缺位")


class NoindexBehaviorTests(FrontendIATestCase):
    """noindex 双消费位行为级验证（前台 meta ＋ sitemap 排除）。"""

    def _publish_article(self, slug):
        from tests.helpers import make_article

        return make_article(self.container, slug=slug, publish=True)

    def test_default_page_indexable_no_robots_meta(self):
        page = self._publish_article("seo-default")
        html = Client().get(page.url).content.decode()
        self.assertNotIn('name="robots"', html, "缺省 False＝默认可收录，不输出 robots meta")

    def test_noindex_page_has_meta_and_left_sitemap(self):
        page = self._publish_article("seo-noindex")
        page.noindex = True
        page.save()

        html = Client().get(page.url).content.decode()
        self.assertIn('<meta name="robots" content="noindex">', html)

        sitemap = Client().get("/sitemap.xml").content.decode()
        self.assertNotIn(f"{page.url}</loc>", sitemap, "noindex 页不入 sitemap.xml")

    def test_indexable_sibling_still_in_sitemap(self):
        """排除仅作用于勾选页本身，同容器其余页不受牵连。"""
        page = self._publish_article("seo-keep")
        sitemap = Client().get("/sitemap.xml").content.decode()
        self.assertIn(f"{page.url}</loc>", sitemap)

    def test_pages_without_field_render_without_meta(self):
        """首页/板块页无 noindex 字段——模板属性查找静默为假，零 meta。"""
        for url in ("/", "/chronicle/"):
            html = Client().get(url).content.decode()
            self.assertNotIn('name="robots"', html, url)

    def test_link_confirm_always_noindex(self):
        """外链确认页整页恒 noindex（F-03 独立位点，不经本字段）。"""
        from urllib.parse import quote

        target = "https://example.com/external"
        html = Client().get(f"/link-confirm/?url={quote(target)}").content.decode()
        self.assertIn('<meta name="robots" content="noindex">', html)
