"""首页数据区与搜索参数回归（Phase 8C 定稿：统一「校园快讯」发现轨）。

断言面：首页页头搜索表单参数＝q（与 /search/ 视图一致，name="query" 串
参数 bug 回归）；层 1 紧急提示（空文案/窗口内外不渲染，§13.4 窗口语径）；
校园快讯统一组稿（至多 3 张卡＝推荐位优先（Q14 创建序；策展失效不占序、
所指 live 页仍公开）→ 最新通知（CURRENT_DEFAULT 谓词 live∧¬expired、
发布倒序）→ 近期活动（活动板块子树、未结束、开始邻近升序、通知/文章双
载体），pk 去重、0 条整区不渲染、旧独立区块零渲染；8C 产品修订：已结束
活动载体经组稿层排除不入轨——既有 event_status 判「已结束」即跳过，
三层输入一视同仁，页面可见性（板块/搜索/详情）不动）；FeaturedItem 模型
级窗口契约（Q15）保留；顺带模板小疵：base.html 不再加载空 peiligo.js、
500.html lang=zh-hans。
"""

import datetime as dt
import json
import re
import shutil
import tempfile
from io import StringIO
from urllib.parse import quote

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from home.models import (
    CAROUSEL_MAX_ITEMS,
    FEATURED_DEFAULT_DAYS,
    CarouselItem,
    FeaturedItem,
    HomePage,
    SectionPage,
    SiteSettings,
)
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import (
    _save,
    body_json,
    future,
    make_article,
    make_container,
    make_department,
    make_notice,
    past,
)
from tests.test_carousel_js import SSR_HIDDEN_ATTR_PATTERN


def _default_site_settings():
    site = Site.objects.get(is_default_site=True)
    settings_obj, _ = SiteSettings.objects.get_or_create(site=site)
    return settings_obj


class HomeAreasTestCase(WagtailPageTestCase):
    """公共基类：五板块就位＋纪事/活动两容器（活动字段仅活动板块可填）。"""

    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_sections", stdout=StringIO())
        cls.sections = {s.slug: s for s in SectionPage.objects.all()}
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.sections["chronicle"], cls.department)
        cls.events_container = make_container(cls.sections["events"], cls.department)

    @classmethod
    def _featured(cls, page, **overrides):
        item = FeaturedItem(content=page, **overrides)
        item.save()
        return item

    @staticmethod
    def _section_html(html, aria_id):
        """截取 aria-labelledby=id 的 <section>…</section> 片段（区块不嵌套）。"""
        pattern = rf'<section[^>]*aria-labelledby="{aria_id}"[^>]*>(.*?)</section>'
        match = re.search(pattern, html, re.DOTALL)
        return match.group(1) if match else ""


class HomeSearchParamTests(HomeAreasTestCase):
    """首页搜索表单参数＝q 回归（合同 §4.2：GET 到现有 /search/）。"""

    def test_form_uses_q_not_query(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="q"')
        self.assertNotContains(response, 'name="query"')

    def test_homepage_form_param_reaches_search(self):
        """首页表单提交（q=唯一词）在 /search/ 命中对应内容（端到端串参）。"""
        make_notice(self.container, slug="q-e2e", title="量子计算 uniqueztoken 通知", publish=True)
        response = self.client.get("/search/", {"q": "uniqueztoken"})
        self.assertEqual(response.status_code, 200)
        # Phase 8B 关键词高亮：命中词包 <mark>，标题连续串被标记打断——
        # 断言改为整行渲染形态（意图不变：该内容在 /search/ 命中）。
        self.assertContains(response, "量子计算 <mark>uniqueztoken</mark> 通知")


class AlertAreaTests(HomeAreasTestCase):
    """层 1 紧急提示：空＝不渲染；成对窗口外不渲染；不限期＝恒渲染。"""

    def test_empty_alert_text_not_rendered(self):
        response = self.client.get("/")
        self.assertNotContains(response, "site-alert")

    def test_blank_whitespace_alert_not_rendered(self):
        settings_obj = _default_site_settings()
        settings_obj.alert_text = "   "
        settings_obj.save()
        response = self.client.get("/")
        self.assertNotContains(response, "site-alert")

    def test_alert_without_window_renders(self):
        settings_obj = _default_site_settings()
        settings_obj.alert_text = "明日校园网络检修通知XYZ"
        settings_obj.save()
        response = self.client.get("/")
        self.assertContains(response, "site-alert")
        self.assertContains(response, "明日校园网络检修通知XYZ")
        self.assertContains(response, 'role="alert"')

    def test_alert_inside_window_renders(self):
        settings_obj = _default_site_settings()
        settings_obj.alert_text = "窗口内提示ABC"
        settings_obj.alert_start_at = past(days=1)
        settings_obj.alert_end_at = future(days=1)
        settings_obj.save()
        response = self.client.get("/")
        self.assertContains(response, "窗口内提示ABC")

    def test_alert_outside_window_not_rendered(self):
        settings_obj = _default_site_settings()
        settings_obj.alert_text = "窗口外提示XYZ"
        cases = [
            {"alert_start_at": past(days=10), "alert_end_at": past(days=1)},  # 已结束
            {"alert_start_at": future(days=1), "alert_end_at": future(days=2)},  # 未开始
        ]
        for window in cases:
            with self.subTest(window=window):
                settings_obj.alert_start_at = window["alert_start_at"]
                settings_obj.alert_end_at = window["alert_end_at"]
                settings_obj.save()
                response = self.client.get("/")
                self.assertNotContains(response, "窗口外提示XYZ")

    def test_alert_is_first_section_before_h1(self):
        """层 1 位次：紧急提示在页面最顶部（h1 之上，IA §7.1）。"""
        settings_obj = _default_site_settings()
        settings_obj.alert_text = "顶部提示TOP"
        settings_obj.save()
        html = self.client.get("/").content.decode()
        self.assertLess(html.index("顶部提示TOP"), html.index("<h1"))


class CampusNewsTests(HomeAreasTestCase):
    """校园快讯统一组稿（Phase 8C）：旧首页「推荐/最新通知/近期活动」三区
    在本页合并为一条至多 3 张卡的发现轨；确定性组稿＝推荐位（创建序）→
    最新通知（发布倒序）→ 近期活动（开始邻近升序），pk 去重；三层输入的
    可见性谓词（§15.4/§16.4）原样生效；已结束活动载体不入轨（8C 产品
    修订：组稿层按既有 event_status 排除，页面可见性不动）。后端数据区
    能力不删（helper 与查询口径见 home.models），仅本页不再按旧区块分别
    渲染。"""

    def _news_section(self, html):
        return self._section_html(html, "news-title")

    def _event_notice(self, slug, title, start_at, end_at):
        """活动结构化字段须直构进模型（make_notice 的 kwargs 语义是 _save 位）。"""
        from notices.models import NoticePage

        host = self.events_container
        return _save(
            NoticePage(
                title=title,
                slug=slug,
                summary="测试摘要",
                department=host.department,
                expire_at=future(),
                body=json.loads(body_json()),
                event_start_at=start_at,
                event_end_at=end_at,
                event_location="大学生活动中心",
            ),
            host,
            publish=True,
        )

    def test_no_entries_section_absent(self):
        """0 条整区不渲染（§7.1 空区不渲染；不渲染巨型空态卡）。"""
        response = self.client.get("/")
        self.assertNotContains(response, "news-title")
        self.assertNotContains(response, "news-card")

    def test_cap_three_priority_featured_then_notices(self):
        """候选 >3：策展条目优先（创建序），余量按最新通知补足，超出截断。"""
        pool = [
            make_notice(self.container, slug=f"cn-pool-{i}", title=f"池内通知{i}", publish=True)
            for i in range(4)
        ]
        self._featured(pool[3])  # 唯一策展条目恰为最新通知，兼验去重
        html = self.client.get("/").content.decode()
        section = self._news_section(html)
        self.assertEqual(section.count('class="news-card'), 3)
        self.assertLess(section.index("池内通知3"), section.index("池内通知2"))
        self.assertLess(section.index("池内通知2"), section.index("池内通知1"))
        self.assertNotIn("池内通知0", section)  # 超出 3 张截断

    def test_dedup_across_sources(self):
        """同一页面只呈现一次：既被策展又属最新通知 → 单卡。"""
        notice = make_notice(self.container, slug="cn-dup", title="去重通知DUP", publish=True)
        self._featured(notice)
        section = self._news_section(self.client.get("/").content.decode())
        self.assertEqual(section.count("去重通知DUP"), 1)

    def test_notices_fill_newest_first_without_featured(self):
        """无策展条目：全部由最新通知补位，发布时间倒序。"""
        make_notice(self.container, slug="cn-old", title="快讯旧N", publish=True)
        make_notice(self.container, slug="cn-new", title="快讯新N", publish=True)
        section = self._news_section(self.client.get("/").content.decode())
        self.assertLess(section.index("快讯新N"), section.index("快讯旧N"))

    def test_draft_and_expired_pages_never_appear(self):
        """CURRENT_DEFAULT 谓词原样生效：草稿/过期页不入轨（任何来源）。"""
        make_notice(self.container, slug="cn-draft", title="草稿快讯DRAFT")
        expired = make_notice(self.container, slug="cn-exp", title="过期快讯EXPIRED", publish=True)
        # 读侧谓词测试以 ORM 直置 expired 位（E7 任务路径已由生命周期测试覆盖）。
        expired.expired = True
        expired.save()
        html = self.client.get("/").content.decode()
        self.assertNotIn("草稿快讯DRAFT", html)
        self.assertNotIn("过期快讯EXPIRED", html)

    def test_withdrawn_curation_keeps_page_public_ordinary_news(self):
        """失效策展（停用）不占策展位与优先序；所指 live 页面仍是公开内容，
        可经通知源以普通快讯出现——8C 统一后「页面可见性」与「策展撤下」
        分层：被撤下的只是策展这一层（与 8B 页面可见性口径一致）。"""
        live_a = make_notice(self.container, slug="cn-vld", title="有效快讯VLD", publish=True)
        self._featured(live_a)
        live_b = make_notice(self.container, slug="cn-off", title="停用策展OFF", publish=True)
        self._featured(live_b, enabled=False)
        html = self.client.get("/").content.decode()
        section = self._news_section(html)
        self.assertIn("有效快讯VLD", section)
        self.assertIn("停用策展OFF", section)
        self.assertLess(section.index("有效快讯VLD"), section.index("停用策展OFF"))

    def test_expired_window_featured_page_still_public_ordinary_news(self):
        """窗口外策展同上：不占策展序，页面经通知源补位。"""
        live_page = make_notice(self.container, slug="cn-end", title="到期策展END", publish=True)
        self._featured(live_page, start_at=past(days=10), end_at=past(days=1))
        section = self._news_section(self.client.get("/").content.decode())
        self.assertIn("到期策展END", section)

    def test_event_entries_carry_status_semantics(self):
        """活动卡随附状态语义（进行中/即将开始）；通知载体的活动通常先经
        通知源入轨（发布倒序），近期活动源仅补足未被认领的条目。"""
        self._event_notice("cn-ev-now", "进行中活动NOW", past(days=1), future(days=1))
        self._event_notice("cn-ev-fut", "未始活动FUT", future(days=2), future(days=3))
        section = self._news_section(self.client.get("/").content.decode())
        self.assertIn("进行中活动NOW", section)
        self.assertIn("未始活动FUT", section)
        self.assertIn("进行中", section)
        self.assertIn("即将开始", section)

    def test_event_source_orders_by_start_and_skips_ended(self):
        """近期活动源谓词/排序原样生效：未结束活动按开始时间邻近升序（文章
        载体仅经此源入轨，可单独观察该源语义）；已结束活动不入该源。"""
        from notices.models import ArticlePage

        host = self.events_container

        def _article(slug, title, start_at, end_at):
            return _save(
                ArticlePage(
                    title=title,
                    slug=slug,
                    summary="测试摘要",
                    department=host.department,
                    body=json.loads(body_json()),
                    event_start_at=start_at,
                    event_end_at=end_at,
                    event_location="体育馆",
                ),
                host,
                publish=True,
            )

        # 创建序（发布倒序）与开始邻近序刻意相反：靠后者先建，若误用发布序
        # 排序则靠后者在前。
        _article("cn-es-late", "活动源靠后L", future(days=5), future(days=6))
        _article("cn-es-soon", "活动源靠前S", future(days=2), future(days=3))
        _article("cn-es-done", "活动源已结D", past(days=10), past(days=5))
        section = self._news_section(self.client.get("/").content.decode())
        self.assertLess(section.index("活动源靠前S"), section.index("活动源靠后L"))
        self.assertNotIn("活动源已结D", section)

    def test_ended_event_notice_excluded_from_campus_news(self):
        """8C 产品修订：已结束的活动载体不入首页发现轨——既有 event_status
        （§7.1 纯计算，与卡面状态标注同源）判「已结束」即整条跳过，通知源
        不再按「live 通知」口径放行（近期活动源本就排除，另测）；正常候选
        照常入轨，不用已结束内容补位。页面自身公开可达性不变（
        test_ended_event_notice_still_public_outside_homepage）。"""
        self._event_notice("cn-ev-old", "已结束活动OLD", past(days=10), past(days=5))
        make_notice(self.container, slug="cn-cur", title="当前通知CUR", publish=True)
        section = self._news_section(self.client.get("/").content.decode())
        self.assertIn("当前通知CUR", section)
        self.assertNotIn("已结束活动OLD", section)
        self.assertNotIn("已结束", section)

    def test_ended_featured_candidate_skipped_not_backfilled(self):
        """排除对三层输入一视同仁：已结束的活动载体即便被策展也不入轨、
        不占策展序；空出槽位由后续来源的正常候选补足（cap 3 语义不变，
        不回填已结束内容）。"""
        ended = self._event_notice("cn-ev-feat", "已结束策展EV", past(days=8), past(days=2))
        self._featured(ended)
        for i in range(3):
            make_notice(self.container, slug=f"cn-fb-{i}", title=f"补位通知{i}", publish=True)
        section = self._news_section(self.client.get("/").content.decode())
        self.assertNotIn("已结束策展EV", section)
        self.assertEqual(section.count('class="news-card'), 3)
        for i in range(3):
            self.assertIn(f"补位通知{i}", section)

    def test_ended_event_notice_still_public_outside_homepage(self):
        """排除仅作用于首页组稿层：页面仍 live/¬expired，详情、板块列表
        （CURRENT_DEFAULT 同谓词）与 /search/ 原样可达——本修订不改任何
        可见性口径。"""
        ended = self._event_notice("cn-ev-old", "已结束活动OLD", past(days=10), past(days=5))
        self.assertFalse(ended.expired)
        detail = self.client.get(ended.url)
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "已结束活动OLD")
        listing = self.client.get("/events/", {"q": "已结束活动OLD"})
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, "已结束活动OLD")
        search = self.client.get("/search/", {"q": "已结束活动OLD"})
        self.assertEqual(search.status_code, 200)
        # 8B 关键词高亮：命中串包 <mark>（整题命中 → 整题被标记）。
        self.assertContains(search, "<mark>已结束活动OLD</mark>")

    def test_article_enters_only_via_curated_or_event_sources(self):
        """无事件字段的文章不经通知源入轨（§7.1 层 3 口径＝通知）；
        策展/活动载体文章仍可入轨（8C 未改变来源定义）。"""
        make_notice(self.container, slug="cn-n", title="来源通知N", publish=True)
        make_article(self.container, slug="cn-a", title="纪事文章A", publish=True)
        section = self._news_section(self.client.get("/").content.decode())
        self.assertIn("来源通知N", section)
        self.assertNotIn("纪事文章A", section)

    def test_old_separate_areas_absent_on_homepage(self):
        """Phase 8C：旧独立「推荐/最新通知/近期活动」区块与独立搜索卡在首页
        零渲染（能力保留、视觉统一；分类可达性由五分类导航承担）。断言锚＝
        各旧区块结构性 id；页脚说明散文中的「五大板块」为 8B 合法文案。"""
        make_notice(self.container, slug="cn-x", title="旧区对照N", publish=True)
        html = self.client.get("/").content.decode()
        for marker in (
            "featured-title",
            "latest-notices-title",
            "upcoming-events-title",
            "search-bench",
        ):
            self.assertNotIn(marker, html)

    def test_card_shows_tag_department_date_and_summary(self):
        """卡片字段全部来自既有数据：板块 tag（浅底 deep 字）＋部门 · 日期
        ＋摘要；颜色不作唯一区分物（tag 内含栏目短名）。"""
        make_notice(self.container, slug="cn-meta", title="元信息卡META", publish=True)
        section = self._news_section(self.client.get("/").content.decode())
        self.assertIn("tone-jishi", section)
        self.assertIn(">纪事</span>", section)
        self.assertIn("教务处", section)
        self.assertIn("<time datetime=", section)
        self.assertIn("测试摘要", section)


class FeaturedItemWindowTests(HomeAreasTestCase):
    """FeaturedItem 模型级窗口契约（Q15，后端能力保留）：默认 30 天为模型
    级默认值；运营动作＝延长（改 end_at）/提前撤下（enabled=False）。首页
    消费侧语义已并入 CampusNewsTests（策展失效不占优先序、页面仍公开）。"""

    def test_q15_default_window_thirty_days(self):
        """Q15 默认 30 天为模型级默认值：留空即起＝当前、止＝起＋30 天。"""
        notice = make_notice(self.container, slug="feat-dft", title="默认窗口推荐", publish=True)
        before = timezone.now()
        item = FeaturedItem(content=notice)
        after = timezone.now()
        self.assertLessEqual(before, item.start_at)
        self.assertLessEqual(item.start_at, after)
        # 起止为两次独立默认求值，窗口长按 1 秒容差断言＝30 天。
        self.assertAlmostEqual(
            (item.end_at - item.start_at).total_seconds(),
            dt.timedelta(days=FEATURED_DEFAULT_DAYS).total_seconds(),
            delta=1,
        )
        item.save()
        self.assertTrue(item.is_on_display())

    def test_q15_extended_and_withdrawn_by_admin(self):
        """Q15 运营动作：延长＝改 end_at；提前撤下＝enabled=False。"""
        notice = make_notice(self.container, slug="feat-ops", title="运营推荐OPS", publish=True)
        item = self._featured(notice)
        item.end_at = future(days=90)
        item.save()
        self.assertTrue(item.is_on_display(future(days=60)))
        item.enabled = False
        item.save()
        self.assertFalse(item.is_on_display())


# ---------------------------------------------------------------------------
# 首页轮播位（首页升级 Phase 6 SSR 基座）：Hero → Carousel → Search 冻结顺序；
# 运行时选择＝home.models._carousel_entries（is_on_display 唯一口径、失效
# 静默跳过、有效项至多 5 个）；外链一律既有确认链路 href；无 JS 时全部
# 条目按文档流自然可达（权威 SSR fallback）。
# ---------------------------------------------------------------------------


def _cover_image(title="轮播封面"):
    """真实 PNG 的 Wagtail Image（依赖调用方类级临时 MEDIA_ROOT，源文件存续
    供 rendition 生成；文件随类末临时目录清理，不入仓库 media/）。"""
    from django.core.files.uploadedfile import SimpleUploadedFile
    from wagtail.images.models import Image

    from .permission_helpers import png_bytes

    img = Image(title=title)
    img.file = SimpleUploadedFile("cover.png", png_bytes(), content_type="image/png")
    img.save()
    return img


class CarouselAreaTestCase(HomeAreasTestCase):
    """轮播位公共基类：类级临时 MEDIA_ROOT 承载封面源图与 rendition 文件
    （进程临时目录类末即清，不落仓库 media/ 与开发者本地 media）。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_tmp = tempfile.mkdtemp(prefix="peiligo-carousel-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_tmp)
        cls._media_override.enable()
        cls.addClassCleanup(cls._media_override.disable)
        cls.addClassCleanup(shutil.rmtree, cls._media_tmp, ignore_errors=True)

    @classmethod
    def _notice_with_cover(cls, slug, title):
        notice = make_notice(cls.container, slug=slug, title=title, publish=True)
        notice.cover_image = _cover_image(f"{title}·封面")
        notice.save()
        return notice

    @staticmethod
    def _carousel_section(html):
        """截取 data-carousel 的 <section>…</section> 片段（区块不嵌套）。"""
        match = re.search(r"<section[^>]*data-carousel[^>]*>(.*?)</section>", html, re.DOTALL)
        return match.group(1) if match else ""


class CarouselZeroItemTests(CarouselAreaTestCase):
    """0 项：Carousel 整区不渲染（§7.1 空区不渲染同语义）。"""

    def test_no_items_carousel_section_absent(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-carousel")
        self.assertNotContains(response, "carousel-item")


class CarouselPlacementTests(CarouselAreaTestCase):
    """SSR 位次（Phase 8C 冻结层级）：Hero 轮播 → 五分类导航 → 校园快讯；
    Hero 即原轮播位（data-carousel 在 hero section 上）。"""

    def test_hero_carousel_precedes_category_nav_and_news(self):
        notice = make_notice(self.container, slug="pos-notice", title="位次通知POS", publish=True)
        CarouselItem(internal_page=notice).save()
        html = self.client.get("/").content.decode()
        hero_at = html.index('class="hero"')
        self.assertLess(hero_at, html.index('aria-label="校园板块"'))
        self.assertLess(hero_at, html.index('id="news-title"'))
        self.assertEqual(html.count("<h1"), 1)  # 全页 h1 唯一（页面主标题）
        self.assertNotIn("<h1", html[hero_at:])  # 轮播条目标题恒 h2


class CarouselInternalItemTests(CarouselAreaTestCase):
    """站内项：title/URL/封面一律取自目标内容页（冻结决策 5），封面取
    cover_image（与正文 image 语义独立）。Phase 8C 面板构图：标题/摘要
    恒在面板（链接可访问名＝面板文字），img 纯装饰（alt=""）。"""

    def test_with_cover_renders_rendition_art(self):
        notice = self._notice_with_cover("cov-in", "封面通知IN")
        CarouselItem(internal_page=notice).save()
        html = self.client.get("/").content.decode()
        section = self._carousel_section(html)
        # 目标页站内 URL 直达（不经确认链路）；输出 rendition 而非裸原图。
        self.assertIn(f'href="{notice.url}"', section)
        self.assertIn("width-1600", section)
        self.assertNotIn("images/cover.png", section)
        # 封面纯装饰；可访问名＝面板可见标题（h2）＋派生摘要。
        self.assertIn('alt=""', section)
        self.assertIn('<h2 class="hero-title">封面通知IN</h2>', section)
        self.assertIn("测试摘要", section)
        self.assertEqual(section.count("封面通知IN"), 1)

    def test_without_cover_renders_frozen_poster(self):
        notice = make_notice(self.container, slug="nocov-in", title="无封面通知IN", publish=True)
        CarouselItem(internal_page=notice).save()
        html = self.client.get("/").content.decode()
        section = self._carousel_section(html)
        self.assertIn(f'href="{notice.url}"', section)
        self.assertIn('<h2 class="hero-title">无封面通知IN</h2>', section)
        self.assertIn("hero-art", section)
        self.assertIn("<svg", section)  # 冻结几何海报回落（无远程图）
        self.assertNotIn("<img", section)


class CarouselExternalItemTests(CarouselAreaTestCase):
    """外链项：一律既有确认链路 href（F-03 contract，无裸外链）；标题在
    面板可见（可访问名），不虚构板块身份（中性「推荐」chip）与摘要。"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.home_pk = HomePage.objects.get().pk

    @staticmethod
    def _item(**overrides):
        defaults = {"external_url": "https://example.com/carousel", "external_title": "外链标题EX"}
        defaults.update(overrides)
        return CarouselItem(**defaults)

    def _confirm_href(self):
        """与 external_link_jump.html 的 urlencode 过滤器同口径（quote(safe="/")）。"""
        encoded = quote("https://example.com/carousel", safe="/")
        return f"/link-confirm/?url={encoded}&amp;from={self.home_pk}"

    def test_with_cover_uses_confirm_href(self):
        item = self._item(external_cover_image=_cover_image("外链封面EX"))
        item.save()
        html = self.client.get("/").content.decode()
        section = self._carousel_section(html)
        self.assertIn(self._confirm_href(), section)
        self.assertNotIn('<a href="https://example.com/carousel"', html)
        # 封面纯装饰；面板可见标题＝可访问名。
        self.assertIn('alt=""', section)
        self.assertIn('<h2 class="hero-title">外链标题EX</h2>', section)
        self.assertEqual(section.count("外链标题EX"), 1)
        # 外链项不虚构摘要（无 hero-sub 输出）。
        self.assertNotIn("hero-sub", section)

    def test_without_cover_renders_poster_and_confirm_href(self):
        self._item().save()
        html = self.client.get("/").content.decode()
        section = self._carousel_section(html)
        self.assertIn(self._confirm_href(), section)
        self.assertIn('<h2 class="hero-title">外链标题EX</h2>', section)
        self.assertNotIn('<a href="https://example.com/carousel"', html)

    def test_confirm_href_lands_on_existing_confirm_page(self):
        """端到端：轮播 confirm href 落在既有确认页（go 阶段二次校验不变）。"""
        self._item().save()
        response = self.client.get(
            "/link-confirm/", {"url": "https://example.com/carousel", "from": str(self.home_pk)}
        )
        self.assertEqual(response.status_code, 200)
        # Phase 8D 展示口径：确认页只展示主机名，完整 URL 不出现。
        self.assertContains(response, 'c-domain">example.com<')
        self.assertNotContains(response, "https://example.com/carousel")
        self.assertContains(response, "继续访问")

    def test_dirty_nonconforming_url_skipped_at_runtime(self):
        """绕过 validator 落库的脏 URL：运行时静默跳过（validate_external_url
        同源复核），不产生任何外链出口，首页不 500。"""
        self._item(external_url="https://user:pass@evil.com/x").save()
        html = self.client.get("/").content.decode()
        self.assertNotIn("data-carousel", html)
        self.assertNotIn("evil.com", html)


class CarouselLifecycleRuntimeTests(CarouselAreaTestCase):
    """站内目标 lifecycle 运行时复核：配置保存后目标转非 live → 运行时
    跳过、首页不 500（§16.4 CURRENT_DEFAULT 同一权威谓词的消费位）。"""

    def test_live_target_shown_then_unpublish_hidden(self):
        notice = make_notice(self.container, slug="lcrt-unpub", title="运行时下线LC", publish=True)
        CarouselItem(internal_page=notice).save()
        self.assertContains(self.client.get("/"), "运行时下线LC")
        notice.unpublish()
        html = self.client.get("/").content.decode()
        self.assertNotIn("运行时下线LC", html)
        self.assertNotIn("data-carousel", html)

    def test_non_live_target_states_all_skipped(self):
        """draft/scheduled/expired 直建即不可见（expired 经 E7 到期路径）。"""
        draft = make_notice(self.container, slug="lcrt-draft", title="运行时草稿LC")
        scheduled = make_notice(
            self.container, slug="lcrt-sched", title="运行时预约LC", schedule_at=future(days=1)
        )
        expired = make_notice(self.container, slug="lcrt-exp", title="运行时到期LC", publish=True)
        type(expired).objects.filter(pk=expired.pk).update(
            expire_at=timezone.now() - dt.timedelta(hours=1)
        )
        call_command("publish_scheduled", verbosity=0)
        expired.refresh_from_db()
        for notice in (draft, scheduled, expired):
            CarouselItem(internal_page=notice).save()
        html = self.client.get("/").content.decode()
        self.assertNotIn("data-carousel", html)
        for title in ("运行时草稿LC", "运行时预约LC", "运行时到期LC"):
            self.assertNotIn(title, html)


class CarouselOrderingTests(CarouselAreaTestCase):
    """排序（冻结决策 10）：sort_order 升序、同值 pk 稳定。"""

    def test_sort_order_then_pk(self):
        """乱序创建：A/B 同 sort_order=0（A 先建 pk 小），C=10 最后呈现。"""
        for i, order in enumerate((0, 0, 10)):
            CarouselItem(
                internal_page=make_notice(
                    self.container, slug=f"ord-{i}", title=f"轮播序{'ABC'[i]}", publish=True
                ),
                sort_order=order,
            ).save()
        section = self._carousel_section(self.client.get("/").content.decode())
        self.assertLess(section.index("轮播序A"), section.index("轮播序B"))
        self.assertLess(section.index("轮播序B"), section.index("轮播序C"))


class CarouselRuntimeCapTests(CarouselAreaTestCase):
    """运行时防御上限（冻结决策 11 消费侧）：按序扫描、过滤后至多 5 个
    有效项；前部失效项被跳过后，后部合法配置补位（不永久遮蔽）。"""

    def test_more_than_five_valid_items_capped(self):
        """绕过 clean 直存 >5 条（save 不触发 full_clean）：前台仍至多 5。"""
        for i in range(CAROUSEL_MAX_ITEMS + 2):
            notice = make_notice(
                self.container, slug=f"cap-{i:02d}", title=f"容量轮播{i:02d}", publish=True
            )
            CarouselItem(internal_page=notice, sort_order=i).save()
        section = self._carousel_section(self.client.get("/").content.decode())
        self.assertEqual(section.count("data-carousel-item"), CAROUSEL_MAX_ITEMS)
        for i in range(CAROUSEL_MAX_ITEMS):
            self.assertIn(f"容量轮播{i:02d}", section)
        for i in (CAROUSEL_MAX_ITEMS, CAROUSEL_MAX_ITEMS + 1):
            self.assertNotIn(f"容量轮播{i:02d}", section)

    def test_invalid_head_items_backfilled_by_valid_tail(self):
        for i in range(2):
            draft = make_notice(self.container, slug=f"bfill-d{i}", title=f"失效头部{i}")
            CarouselItem(internal_page=draft, sort_order=i).save()
        for i in range(CAROUSEL_MAX_ITEMS):
            notice = make_notice(
                self.container, slug=f"bfill-v{i}", title=f"补位轮播{i}", publish=True
            )
            CarouselItem(internal_page=notice, sort_order=10 + i).save()
        section = self._carousel_section(self.client.get("/").content.decode())
        self.assertEqual(section.count("data-carousel-item"), CAROUSEL_MAX_ITEMS)
        for i in range(CAROUSEL_MAX_ITEMS):
            self.assertIn(f"补位轮播{i}", section)
        for i in range(2):
            self.assertNotIn(f"失效头部{i}", section)


class CarouselEscapingTests(CarouselAreaTestCase):
    """XSS（TASK I）：external_title 为不可信运营输入，恒经默认转义，
    任何输出上下文不得出现可执行 markup。"""

    def test_hostile_external_title_escaped_in_img_attribute(self):
        """最严上下文＝img alt 属性：script 标签与引号逃逸均不得存活。"""
        item = CarouselItem(
            external_url="https://example.com/xss",
            external_title='<script>alert(1)</script>"onmouseover="x',
            external_cover_image=_cover_image("XSS封面"),
        )
        item.save()
        html = self.client.get("/").content.decode()
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_hostile_external_title_escaped_in_fallback_text(self):
        item = CarouselItem(
            external_url="https://example.com/xss2",
            external_title="<script>alert(2)</script>",
        )
        item.save()
        html = self.client.get("/").content.decode()
        self.assertNotIn("<script>alert(2)</script>", html)
        self.assertIn("&lt;script&gt;alert(2)&lt;/script&gt;", html)


class CarouselNoJsFallbackTests(CarouselAreaTestCase):
    """无 JS 权威 fallback（TASK H）：多 item 全部按文档流 SSR 输出，
    无隐藏态；data hooks 仅作结构标记，不承载内容与 inline JS。"""

    def test_all_items_present_in_document_flow(self):
        for i in range(3):
            notice = make_notice(
                self.container, slug=f"nojs-{i}", title=f"无JS轮播{i}", publish=True
            )
            CarouselItem(internal_page=notice).save()
        html = self.client.get("/").content.decode()
        section = self._carousel_section(html)
        self.assertEqual(section.count("data-carousel-item"), 3)
        for i in range(3):
            self.assertIn(f"无JS轮播{i}", section)
        # 可见性断言为属性级（aria-hidden 装饰标注不算可见性状态），
        # 与 test_carousel_js 的 SSR_HIDDEN_ATTR_PATTERN 同一口径。
        self.assertIsNone(SSR_HIDDEN_ATTR_PATTERN.search(section))
        self.assertNotIn("display:none", section)
        self.assertNotIn("<script", section)


class TemplateNibTests(HomeAreasTestCase):
    """顺带小疵：空 peiligo.js 不再加载；500 页 lang=zh-hans。"""

    def test_base_html_has_no_empty_script(self):
        response = self.client.get("/")
        self.assertNotContains(response, "js/peiligo.js")

    def test_500_page_is_chinese(self):
        with open("templates/500.html", encoding="utf-8") as fh:
            template_html = fh.read()
        self.assertIn('lang="zh-hans"', template_html)
        self.assertNotIn('lang="en"', template_html)
