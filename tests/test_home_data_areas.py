"""F-04 首页四数据区与搜索参数回归（IA §7.1/§7.2；G2_HUMAN_DECISIONS Q14/Q15）。

断言面：首页搜索表单参数＝q（与 /search/ 视图一致，name="query" 串参数
bug 回归）；层 1 紧急提示（空文案/窗口内外不渲染，§13.4 窗口语径）；层 2
推荐位（有效条目创建序最多 3＝Q14、0 条整区不渲染、1–2 自然呈现、无效
条目不占槽位、Q15 默认 30 天窗口为模型级默认值）；层 3 最新通知
（CURRENT_DEFAULT 谓词 live∧¬expired、发布时间倒序、条数截断）；层 4
近期活动（活动板块子树、未结束、开始时间邻近升序、通知/文章双载体）；
顺带模板小疵：base.html 不再加载空 peiligo.js、500.html lang=zh-hans。
"""

import datetime as dt
import json
import re
from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from home.models import (
    FEATURED_DEFAULT_DAYS,
    FEATURED_MAX_SLOTS,
    FeaturedItem,
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
        self.assertContains(response, "量子计算 uniqueztoken 通知")


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


class FeaturedAreaTests(HomeAreasTestCase):
    """层 2 推荐位：≤3（Q14）、0 隐藏、无效不占槽、创建序呈现。"""

    def test_no_items_section_absent(self):
        response = self.client.get("/")
        self.assertNotContains(response, "featured-title")
        self.assertNotContains(response, ">推荐</h2>")

    def test_one_or_two_items_render_naturally(self):
        notices = [
            make_notice(self.container, slug=f"feat-{i}", title=f"推荐内容{i}", publish=True)
            for i in range(2)
        ]
        for notice in notices:
            self._featured(notice)
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "featured-title")
        for i in range(2):
            self.assertIn(f"推荐内容{i}", section)

    def test_cap_three_slots_creation_order(self):
        """Q14：有效条目 >3 只呈现创建顺序前 3（pk 升序）。"""
        for i in range(5):
            notice = make_notice(
                self.container, slug=f"cap-{i}", title=f"槽位内容{i}", publish=True
            )
            self._featured(notice)
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "featured-title")
        self.assertEqual(section.count("<li>"), FEATURED_MAX_SLOTS)
        for i in range(3):
            self.assertIn(f"槽位内容{i}", section)
        for i in (3, 4):
            self.assertNotIn(f"槽位内容{i}", section)

    def test_disabled_or_out_of_window_or_nonlive_excluded(self):
        live = make_notice(self.container, slug="feat-live", title="有效推荐LIVE", publish=True)
        self._featured(live)

        disabled_content = make_notice(
            self.container, slug="feat-off", title="停用推荐OFF", publish=True
        )
        self._featured(disabled_content, enabled=False)

        ended_content = make_notice(
            self.container, slug="feat-end", title="到期推荐END", publish=True
        )
        self._featured(ended_content, start_at=past(days=10), end_at=past(days=1))

        not_started_content = make_notice(
            self.container, slug="feat-fut", title="未始推荐FUT", publish=True
        )
        self._featured(not_started_content, start_at=future(days=1), end_at=future(days=9))

        draft = make_notice(self.container, slug="feat-draft", title="草稿推荐DRAFT")
        self.assertFalse(draft.live)
        self._featured(draft)

        html = self.client.get("/").content.decode()
        section = self._section_html(html, "featured-title")
        self.assertIn("有效推荐LIVE", section)
        for absent in ("停用推荐OFF", "到期推荐END", "未始推荐FUT", "草稿推荐DRAFT"):
            self.assertNotIn(absent, section)

    def test_invalid_items_do_not_occupy_slots(self):
        """窗口外/停用条目不占槽位：2 有效＋2 无效仍呈现 2 条有效＋后补 1。"""
        for i in range(3):
            notice = make_notice(
                self.container, slug=f"vld-{i}", title=f"有效槽位V{i}", publish=True
            )
            self._featured(notice)
        invalid1 = make_notice(self.container, slug="inv-1", title="无效槽位I1", publish=True)
        self._featured(invalid1, enabled=False)
        invalid2 = make_notice(self.container, slug="inv-2", title="无效槽位I2", publish=True)
        self._featured(invalid2, start_at=past(days=9), end_at=past(days=2))
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "featured-title")
        self.assertEqual(section.count("<li>"), 3)
        for i in range(3):
            self.assertIn(f"有效槽位V{i}", section)

    def test_expired_content_not_displayed(self):
        """所指内容 S3（expired）不展示（§15.4 lifecycle live 条件）。"""
        notice = make_notice(self.container, slug="feat-exp", title="已过期推荐EXP", publish=True)
        # 读侧谓词测试以 ORM 直置 expired 位（E7 任务路径已由生命周期测试覆盖）。
        notice.expired = True
        notice.save()
        self._featured(notice)
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "featured-title")
        self.assertEqual(section, "")

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


class LatestNoticesTests(HomeAreasTestCase):
    """层 3 最新通知：CURRENT_DEFAULT 谓词、发布倒序、条数截断。"""

    def test_only_live_unexpired_notices_newest_first(self):
        make_notice(self.container, slug="ln-1", title="旧通知FIRST", publish=True)
        make_notice(self.container, slug="ln-2", title="新通知SECOND", publish=True)
        make_notice(self.container, slug="ln-draft", title="草稿通知DRAFT")
        expired = make_notice(self.container, slug="ln-exp", title="过期通知EXPIRED", publish=True)
        expired.expired = True
        expired.save()

        html = self.client.get("/").content.decode()
        section = self._section_html(html, "latest-notices-title")
        self.assertIn("新通知SECOND", section)
        self.assertIn("旧通知FIRST", section)
        self.assertNotIn("草稿通知DRAFT", section)
        self.assertNotIn("过期通知EXPIRED", section)
        self.assertLess(section.index("新通知SECOND"), section.index("旧通知FIRST"))

    def test_count_truncated_to_parameter(self):
        from home.models import HOMEPAGE_LATEST_NOTICES_COUNT

        for i in range(HOMEPAGE_LATEST_NOTICES_COUNT + 2):
            make_notice(self.container, slug=f"cnt-{i:02d}", title=f"计数通知{i:02d}", publish=True)
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "latest-notices-title")
        self.assertEqual(section.count("<li>"), HOMEPAGE_LATEST_NOTICES_COUNT)
        # 倒序截断：最旧两条不入（发布序最小）。
        self.assertNotIn("计数通知00", section)
        self.assertNotIn("计数通知01", section)
        self.assertIn(f"计数通知{HOMEPAGE_LATEST_NOTICES_COUNT + 1:02d}", section)

    def test_articles_are_not_notices(self):
        """层 3 仅通知：文章不入最新通知区（IA §7.1 口径＝通知）。"""
        make_notice(self.container, slug="ln-notice", title="层级通知N", publish=True)
        make_article(self.container, slug="ln-article", title="层级文章A", publish=True)
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "latest-notices-title")
        self.assertIn("层级通知N", section)
        self.assertNotIn("层级文章A", section)


class UpcomingEventsTests(HomeAreasTestCase):
    """层 4 近期活动：活动板块子树、未结束、开始时间邻近升序、双载体。"""

    def _event_notice(
        self, slug, title, start_at, end_at, container=None, location="大学生活动中心"
    ):
        """活动结构化字段须直构进模型（make_notice 的 kwargs 语义是 _save 位）。"""
        from notices.models import NoticePage

        host = container or self.events_container
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
                event_location=location,
            ),
            host,
            publish=True,
        )

    def _event_article(self, slug, title, start_at, end_at):
        from notices.models import ArticlePage

        return _save(
            ArticlePage(
                title=title,
                slug=slug,
                summary="测试摘要",
                department=self.events_container.department,
                body=json.loads(body_json()),
                event_start_at=start_at,
                event_end_at=end_at,
                event_location="体育馆",
            ),
            self.events_container,
            publish=True,
        )

    def test_upcoming_event_renders_in_order(self):
        self._event_notice("ev-later", "活动靠后B", future(days=5), future(days=6))
        self._event_notice("ev-earlier", "活动靠前A", future(days=2), future(days=3))
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "upcoming-events-title")
        self.assertIn("活动靠前A", section)
        self.assertIn("活动靠后B", section)
        self.assertLess(section.index("活动靠前A"), section.index("活动靠后B"))
        # 卡片带活动状态语义（content_card 的 event_status 位）。
        self.assertIn("即将开始", section)

    def test_ongoing_event_included_past_event_excluded(self):
        self._event_notice("ev-ongoing", "进行中活动NOW", past(days=1), future(days=1))
        self._event_notice("ev-past", "已结束活动OLD", past(days=10), past(days=5))
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "upcoming-events-title")
        self.assertIn("进行中活动NOW", section)
        self.assertNotIn("已结束活动OLD", section)

    def test_only_events_section_subtree(self):
        """纪事板块页面（活动字段强制留空）与无活动字段页不入近期活动。"""
        self._event_notice("ev-events", "活动板块活动IN", future(days=3), future(days=4))
        make_notice(self.container, slug="ev-plain", title="无活动字段N", publish=True)
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "upcoming-events-title")
        self.assertIn("活动板块活动IN", section)
        self.assertNotIn("无活动字段N", section)

    def test_article_carries_event_too(self):
        """活动载体含文章（§7 结构化活动字段挂通知/文章两类）。"""
        self._event_article("ev-article", "文章载体活动ART", future(days=4), future(days=5))
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "upcoming-events-title")
        self.assertIn("文章载体活动ART", section)

    def test_mixed_models_sorted_by_event_start(self):
        """通知/文章两载体合并后按活动开始时间统一升序截断。"""
        from home.models import HOMEPAGE_UPCOMING_EVENTS_COUNT

        self._event_notice("ev-m0", "合并活动M0", future(days=1), future(days=2))
        self._event_article("ev-m1", "合并活动M1", future(days=2), future(days=3))
        self._event_notice("ev-m2", "合并活动M2", future(days=3), future(days=4))
        html = self.client.get("/").content.decode()
        section = self._section_html(html, "upcoming-events-title")
        self.assertLessEqual(section.count("<li>"), HOMEPAGE_UPCOMING_EVENTS_COUNT)
        self.assertLess(section.index("合并活动M1"), section.index("合并活动M2"))


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
