"""A3.1 活动字段（EventFieldsMixin）测试（CONTENT_MODEL §2/§7）。

- 零 EventPage（§2 终判：仅 Mixin 挂 Notice/Article，不建独立活动页）；
- §7.2 板块适用规则：events 起止必填/线下必填地点/线上免地点；
  chronicle 五字段强制全空（防误填双保险）；
- §7.1 成对校验与 end ≥ start（相等合法）；
- CM-03 三态纯计算（闭区间，按当前时间）。
"""

import datetime as dt

from django.apps import apps
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from notices.models import ArticlePage, EventFieldsMixin, NoticePage
from wagtail.models import Page

from .helpers import article_data, build_sections, make_container, make_department

UTC = dt.UTC


class NoEventPageTests(TestCase):
    """§2 类型组织终判：EventFieldsMixin 纯抽象、仅双页继承、零 EventPage。"""

    def test_mixin_is_abstract(self):
        self.assertTrue(EventFieldsMixin._meta.abstract)

    def test_no_page_subclass_named_event(self):
        for model in apps.get_models():
            if issubclass(model, Page):
                self.assertNotIn(
                    "EventPage",
                    model.__name__,
                    msg=f"{model.__name__} 疑似独立活动页（§2：不得建 EventPage）",
                )

    def test_mixin_inherited_only_by_notice_and_article(self):
        concrete = [
            model
            for model in apps.get_models()
            if issubclass(model, EventFieldsMixin) and not model._meta.abstract
        ]
        self.assertEqual(set(concrete), {NoticePage, ArticlePage})

    def test_mixin_fields_not_on_other_content_types(self):
        from guides.models import GuidePage
        from resources.models import MaterialPage, SoftwareToolPage

        for model in (MaterialPage, SoftwareToolPage, GuidePage):
            with self.subTest(model=model.__name__):
                for field_name in (
                    "event_start_at",
                    "event_end_at",
                    "event_location",
                    "event_is_online",
                    "event_registration_url",
                ):
                    self.assertNotIn(
                        field_name,
                        [f.name for f in model._meta.get_fields()],
                    )


class EventSectionRulesBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("学生处", "xsc")
        cls.events_container = make_container(sections["events"], cls.department)
        cls.chronicle_container = make_container(
            sections["chronicle"], make_department("教务处", "jwc")
        )

    def make_notice(self, **kwargs):
        """未入库 NoticePage（挂在指定容器的提交流程父级上）。"""
        page = NoticePage(
            title="测试通知",
            slug="ev-test",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=self.events_container.department,
            expire_at=dt.datetime(2026, 12, 31, 23, 0, tzinfo=UTC),
            **kwargs,
        )
        page._provisional_parent = self.events_container
        return page

    def clean_errors(self, page):
        """跑 clean() 并返回 field→messages 的映射（不触树内建字段校验）。"""
        try:
            page.clean()
        except ValidationError as e:
            return e.message_dict
        return {}


class EventFieldsInSectionTests(EventSectionRulesBase):
    """§7.2：校园活动板块下起止必填、线下必填地点。"""

    def test_missing_start_rejected(self):
        errors = self.clean_errors(
            self.make_notice(
                event_start_at=None,
                event_end_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
                event_location="大礼堂",
            )
        )
        self.assertIn("必须填写开始时间", str(errors.get("event_start_at", "")))

    def test_missing_end_rejected(self):
        errors = self.clean_errors(
            self.make_notice(
                event_start_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                event_location="大礼堂",
            )
        )
        self.assertIn("必须填写结束时间", str(errors.get("event_end_at", "")))

    def test_offline_without_location_rejected(self):
        errors = self.clean_errors(
            self.make_notice(
                event_start_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                event_end_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
                event_location="",
            )
        )
        self.assertIn("线下活动必须填写活动地点", str(errors.get("event_location", "")))

    def test_online_without_location_accepted(self):
        page = self.make_notice(
            event_start_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            event_end_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
            event_is_online=True,
        )
        self.assertEqual(self.clean_errors(page), {})

    def test_end_before_start_rejected_and_equal_legal(self):
        bad = self.make_notice(
            event_start_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
            event_end_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            event_location="大礼堂",
        )
        self.assertIn("不得早于开始时间", str(self.clean_errors(bad).get("event_end_at", "")))
        same = dt.datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
        ok = self.make_notice(event_start_at=same, event_end_at=same, event_location="大礼堂")
        self.assertEqual(self.clean_errors(ok), {})

    def test_registration_url_validated_by_urlfield(self):
        """报名链接是 URLField：非 URL 值经表单字段校验拒绝。"""
        from .helpers import notice_data

        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(
                self.events_container,
                event_start_at="2026-09-01 10:00:00",
                event_end_at="2026-09-01 12:00:00",
                event_is_online="on",
                event_registration_url="不是网址",
            ),
            parent_page=self.events_container,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("event_registration_url", form.errors)


class EventFieldsInChronicleTests(EventSectionRulesBase):
    """§7.2：校园纪事板块下五字段强制全空（防误填双保险）。"""

    def _chronicle_notice(self, **kwargs):
        page = NoticePage(
            title="纪事通知",
            slug="chr-test",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=self.chronicle_container.department,
            expire_at=dt.datetime(2026, 12, 31, 23, 0, tzinfo=UTC),
            **kwargs,
        )
        page._provisional_parent = self.chronicle_container
        return page

    def test_all_empty_accepted(self):
        self.assertEqual(self.clean_errors(self._chronicle_notice()), {})

    def test_any_filled_rejected(self):
        cases = {
            "event_start_at": dt.datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            "event_end_at": dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
            "event_location": "大礼堂",
            "event_is_online": True,
            "event_registration_url": "https://example.com/r",
        }
        for field_name, value in cases.items():
            with self.subTest(field=field_name):
                errors = self.clean_errors(self._chronicle_notice(**{field_name: value}))
                self.assertIn("活动字段须留空", str(errors.get(field_name, "")))

    def test_article_in_chronicle_with_event_fields_rejected_via_form(self):
        """文章页同规则（Mixin 双页一致）：表单流全链验证。"""
        form = ArticlePage.get_edit_handler().get_form_class()(
            data=article_data(
                self.chronicle_container,
                event_start_at="2026-09-01 10:00:00",
                event_end_at="2026-09-01 12:00:00",
                event_location="大礼堂",
            ),
            parent_page=self.chronicle_container,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("活动字段须留空", str(form.errors))


class EventStatusPropertyTests(EventSectionRulesBase):
    """CM-03：三态纯计算（起止闭区间对比当前时间；未填无状态）。"""

    def _page(self, start, end):
        return NoticePage(event_start_at=start, event_end_at=end)

    def test_upcoming(self):
        page = self._page(
            timezone.now() + dt.timedelta(days=1),
            timezone.now() + dt.timedelta(days=2),
        )
        self.assertEqual(page.event_status, EventFieldsMixin.STATUS_UPCOMING)

    def test_ongoing_closed_interval(self):
        now = timezone.now()
        page = self._page(now - dt.timedelta(hours=1), now + dt.timedelta(hours=1))
        self.assertEqual(page.event_status, EventFieldsMixin.STATUS_ONGOING)

    def test_ended(self):
        page = self._page(
            timezone.now() - dt.timedelta(days=2),
            timezone.now() - dt.timedelta(days=1),
        )
        self.assertEqual(page.event_status, EventFieldsMixin.STATUS_ENDED)

    def test_no_status_without_dates(self):
        self.assertIsNone(self._page(None, None).event_status)

    def test_status_is_pure_computation_no_storage(self):
        """三态按起止纯计算：无存储字段/无前台消费（消费属 M3.3）。"""
        self.assertNotIn("event_status", [f.name for f in NoticePage._meta.get_fields()])
