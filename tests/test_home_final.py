"""Phase 8C 首页定稿验收（R4-A「Peiligo POP」冻结层级）。

断言面（8C 任务验收清单）：
- 冻结层级结构序：Header → [紧急提示（例外条）] → h1 → Hero 轮播 →
  五分类导航 → 校园快讯 → Footer；空数据区整区不渲染；
- Hero 派生数据（8A 冻结：仅运行时派生键，无持久字段）：站内项 chip＝
  板块短名、摘要＝既有字段链截断；外链项中性「推荐」chip、不虚构摘要；
- CarouselItem 模型零新增展示字段（不新增 subtitle/chip/theme 等字段）；
- 五分类导航恰五项、每板块链接全页恰一次、身份类冻结（cat-<tone>）；
- 校园快讯 1/2/3 卡自然呈现（>3 截断、去重、组稿序见 test_home_data_areas）；
- 全页零远程资产（脚本/样式/图片无外链）与零 inline 事件处理器；
- 1 项静态 Hero：SSR 单条目、零控件（控件仅 JS 增强 ≥2 项时创建）。
"""

import json
import re
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase
from home.models import CarouselItem, SectionPage
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import (
    _save,
    body_json,
    future,
    make_container,
    make_department,
    make_notice,
    make_software,
)

# 冻结 SECTION_IDENTITY tone 映射（§5.2；peiligo_extras.section_tone 同源，
# 在此独立冻结以防映射漂移——改动须显式改本表并说明）。
FROZEN_CAT_TONE_BY_SLUG = {
    "chronicle": "jishi",
    "events": "huodong",
    "materials": "ziliao",
    "software": "gongju",
    "guide": "zhinan",
}

# 8A 冻结：CarouselItem 具体字段集（派生展示键 summary/section_slug 只在
# 运行时 dict 上，绝不落入模型——新增任何字段都会使本断言失败）。
FROZEN_CAROUSEL_ITEM_FIELDS = {
    "id",
    "internal_page",
    "external_url",
    "external_title",
    "external_cover_image",
    "sort_order",
}


class FinalHomePageTestCase(WagtailPageTestCase):
    """公共基类：五板块就位＋纪事容器。"""

    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_sections", stdout=StringIO())
        cls.sections = {s.slug: s for s in SectionPage.objects.all()}
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.sections["chronicle"], cls.department)
        cls.software_container = make_container(cls.sections["software"], cls.department)


class HomePageStructureOrderTests(FinalHomePageTestCase):
    """冻结层级：Header → [紧急提示] → h1 → Hero → 五分类导航 → 校园快讯 → Footer。"""

    def test_frozen_order_with_all_sections_present(self):
        hero_notice = make_notice(self.container, slug="ord-hero", title="层级通知H", publish=True)
        CarouselItem(internal_page=hero_notice).save()
        make_notice(self.container, slug="ord-news", title="层级通知N", publish=True)
        html = self.client.get("/").content.decode()
        header_at = html.index('class="site-header"')
        h1_at = html.index("<h1")
        hero_at = html.index('class="hero"')
        cats_at = html.index('aria-label="校园板块"')
        news_at = html.index('id="news-title"')
        footer_at = html.index('class="site-footer"')
        self.assertLess(header_at, h1_at)
        self.assertLess(h1_at, hero_at)
        self.assertLess(hero_at, cats_at)
        self.assertLess(cats_at, news_at)
        self.assertLess(news_at, footer_at)
        # 全页恒一个 h1（视觉隐藏页面标题；轮播条目/卡片标题均 h2/h3）。
        self.assertEqual(html.count("<h1"), 1)

    def test_alert_sits_between_header_and_h1(self):
        from tests.test_home_data_areas import _default_site_settings

        settings_obj = _default_site_settings()
        settings_obj.alert_text = "层级紧急提示ORDER"
        settings_obj.save()
        html = self.client.get("/").content.decode()
        self.assertLess(html.index('class="site-header"'), html.index('class="site-alert"'))
        self.assertLess(html.index('class="site-alert"'), html.index("<h1"))

    def test_empty_home_renders_h1_and_cats_only(self):
        """0 轮播项、0 快讯：整区不渲染；五分类导航恒在（结构入口）。"""
        html = self.client.get("/").content.decode()
        self.assertNotIn("data-carousel", html)
        self.assertNotIn("news-title", html)
        self.assertIn('<h1 class="visually-hidden">首页</h1>', html)
        self.assertIn('aria-label="校园板块"', html)


class HeroDerivedDataTests(FinalHomePageTestCase):
    """Hero 派生键契约（8A）：站内项 chip＝板块短名＋既有字段链摘要；
    外链项中性「推荐」chip、零虚构摘要（section 身份不可得即不猜）。"""

    def _notice_with_summary(self, slug, title, summary):
        """自定义摘要的通知（make_notice 固定 summary="测试摘要"，此处须直构）。"""
        from notices.models import NoticePage

        return _save(
            NoticePage(
                title=title,
                slug=slug,
                summary=summary,
                department=self.container.department,
                expire_at=future(),
                body=json.loads(body_json()),
            ),
            self.container,
            publish=True,
        )

    def test_internal_item_derives_chip_and_summary(self):
        notice = self._notice_with_summary("hero-in", "站内主推IN", "主推摘要SUM")
        CarouselItem(internal_page=notice).save()
        html = self.client.get("/").content.decode()
        section = re.search(r'<section class="hero"[^>]*>(.*?)</section>', html, re.DOTALL).group(1)
        self.assertIn('<span class="hero-chip">纪事</span>', section)
        self.assertIn('<h2 class="hero-title">站内主推IN</h2>', section)
        self.assertIn('<p class="hero-sub">主推摘要SUM</p>', section)
        self.assertIn('href="/chronicle/jwc/hero-in/"', section)

    def test_external_item_neutral_chip_no_summary(self):
        CarouselItem(external_url="https://example.com/hero", external_title="外链主推EX").save()
        html = self.client.get("/").content.decode()
        section = re.search(r'<section class="hero"[^>]*>(.*?)</section>', html, re.DOTALL).group(1)
        self.assertIn('<span class="hero-chip">推荐</span>', section)
        self.assertIn('<h2 class="hero-title">外链主推EX</h2>', section)
        self.assertNotIn("hero-sub", section)

    def test_blank_summary_chain_outputs_no_hero_sub(self):
        """既有字段链尾（软件 license_note）为空 → Hero 不输出摘要位，不发明
        新文案（链：summary → license_note → location，同 list_row 口径；
        notice/article/material 的 summary 为必填，链尾空位仅软件/指南可达）。"""
        from resources.models import SoftwareToolPage

        page = make_software(
            self.software_container, slug="hero-sw", title="无简介主推SW", publish=True
        )
        SoftwareToolPage.objects.filter(pk=page.pk).update(license_note="")
        CarouselItem(internal_page=page).save()
        section = re.search(
            r'<section class="hero"[^>]*>(.*?)</section>',
            self.client.get("/").content.decode(),
            re.DOTALL,
        ).group(1)
        self.assertNotIn("hero-sub", section)
        self.assertIn('<h2 class="hero-title">无简介主推SW</h2>', section)


class CarouselItemFrozenFieldsTests(SimpleTestCase):
    """8A 冻结：CarouselItem 零新增展示字段（Hero 的 summary/section_slug
    为运行时派生键；新增 subtitle/chip/cta_text/theme 等字段即失败）。"""

    def test_carousel_item_concrete_fields_exactly_frozen_set(self):
        concrete = {
            field.name
            for field in CarouselItem._meta.get_fields()
            if getattr(field, "concrete", False)
        }
        self.assertEqual(concrete, FROZEN_CAROUSEL_ITEM_FIELDS)


class CategoryNavFinalTests(FinalHomePageTestCase):
    """五分类导航：恰五项、每板块链接全页恰一次、冻结身份类。"""

    def test_each_section_linked_exactly_once_per_page(self):
        make_notice(self.container, slug="nav-n", title="导航对照N", publish=True)
        html = self.client.get("/").content.decode()
        for slug in FROZEN_CAT_TONE_BY_SLUG:
            with self.subTest(slug=slug):
                self.assertEqual(html.count(f'href="/{slug}/"'), 1)

    def test_nav_is_the_only_category_surface(self):
        """五分类入口只在 cats 导航出现一次（Header 不重复导航）。"""
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count('aria-label="校园板块"'), 1)
        nav = re.search(r'<nav class="cats"[^>]*>(.*?)</nav>', html, re.DOTALL).group(1)
        self.assertEqual(len(re.findall(r'<a class="cat cat-', nav)), 5)


class CampusNewsShapeTests(FinalHomePageTestCase):
    """校园快讯低数据形态：1/2/3 卡自然呈现（0 条整区不渲染）。"""

    def _news_html(self, count):
        for i in range(count):
            make_notice(self.container, slug=f"shape-{i}", title=f"形态通知{i}", publish=True)
        return self.client.get("/").content.decode()

    def test_one_card_renders(self):
        html = self._news_html(1)
        self.assertEqual(html.count('class="news-card'), 1)

    def test_two_cards_render(self):
        html = self._news_html(2)
        self.assertEqual(html.count('class="news-card'), 2)

    def test_three_cards_render(self):
        html = self._news_html(3)
        self.assertEqual(html.count('class="news-card'), 3)

    def test_cards_use_section_art_fallback_without_cover(self):
        """无封面卡＝板块静态几何插画（同一几何语言，无逐条生成、无远程图）。"""
        html = self._news_html(1)
        self.assertIn('class="news-art"', html)
        self.assertIn('viewBox="0 0 400 260"', html)


class SingleItemStaticHeroTests(FinalHomePageTestCase):
    """1 项 Hero：SSR 单条目、零控件（Phase 7：控件仅 JS 在 ≥2 项时创建）。"""

    def test_single_item_no_server_controls(self):
        single_notice = make_notice(
            self.container, slug="single-h", title="单项主推S1", publish=True
        )
        CarouselItem(internal_page=single_notice).save()
        html = self.client.get("/").content.decode()
        section = re.search(r'<section class="hero"[^>]*>(.*?)</section>', html, re.DOTALL).group(1)
        self.assertEqual(section.count("data-carousel-item"), 1)
        self.assertNotIn("<button", section)
        self.assertNotIn("data-carousel-controls", section)
        self.assertNotIn("data-carousel-enhanced", html)


class HomePageHygieneTests(FinalHomePageTestCase):
    """资产与行为卫生：零远程资产、零 inline 事件处理器、单脚本。"""

    def test_no_remote_assets_anywhere(self):
        """脚本/样式/图片零外链（无 CDN/字体服务/远程图；外链内容仅经
        /link-confirm/ 确认链路，其 url 参数已编码不构成资源外链）。"""
        make_notice(self.container, slug="hyg-n", title="卫生对照N", publish=True)
        CarouselItem(external_url="https://example.com/hyg", external_title="外链卫生EX").save()
        html = self.client.get("/").content.decode()
        self.assertEqual(re.findall(r'(?:src|href)="(?:https?:)?//', html), [])
        for vendor in ("fonts.googleapis", "fonts.gstatic", "cdnjs", "jsdelivr", "unpkg"):
            with self.subTest(vendor=vendor):
                self.assertNotIn(vendor, html)

    def test_no_inline_event_handlers(self):
        make_notice(self.container, slug="hyg-h", title="内联对照H", publish=True)
        html = self.client.get("/").content.decode()
        self.assertEqual(re.findall(r"\son[a-z]+=\"", html), [])
        for handler in ("onclick=", "onmouseover=", "onerror=", "onload="):
            with self.subTest(handler=handler):
                self.assertNotIn(handler, html)

    def test_homepage_loads_single_local_script(self):
        html = self.client.get("/").content.decode()
        srcs = re.findall(r'<script\b[^>]*\bsrc="([^"]*)"', html)
        self.assertEqual(srcs, ["/static/js/carousel.js"])
