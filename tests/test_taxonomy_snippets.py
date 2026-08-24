"""A3.1 受控词表/Snippet 测试（CONTENT_MODEL §13）。

- Department：名称/代号双唯一、排序、停用默认值（§13.1）；
- 四类别词表同构两字段（§13.2）；
- FeaturedItem：起止成对 end≥start、选择器仅五类内容页（§13.3）；
- SiteSettings：起止同时填/同时空＋止≥起、反馈邮箱必填（§13.4）；
- 迁移零漂移：makemigrations --check 实测（任务批令自测项）。
"""

import datetime as dt

from departments.models import Department
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from guides.models import GuideCategory, GuidePage
from home.models import FeaturedItem, SiteSettings
from notices.models import ArticlePage, NoticePage
from resources.models import Discipline, MaterialPage, MaterialType, Platform, SoftwareToolPage
from wagtail.admin.widgets import AdminPageChooser

from .helpers import make_department

UTC = dt.UTC


class DepartmentTests(TestCase):
    def test_uniqueness_on_name_and_slug(self):
        Department.objects.create(name="教务处", slug="jwc")
        # transaction.atomic：吞掉 IntegrityError 后修复测试事务（Postgres 口径）。
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Department.objects.create(name="教务处", slug="other")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Department.objects.create(name="科研处", slug="jwc")

    def test_defaults_and_ordering(self):
        d1 = Department.objects.create(name="乙部门", slug="b")
        d2 = Department.objects.create(name="甲部门", slug="a", sort_order=-1)
        self.assertTrue(d1.is_active)
        self.assertEqual(d1.sort_order, 0)
        self.assertEqual(list(Department.objects.all()), [d2, d1])


class VocabularyShapeTests(TestCase):
    """§13.2：四类别词表字段仅两枚（名称唯一＋排序）。"""

    def test_two_field_vocabularies(self):
        for model in (Discipline, MaterialType, Platform, GuideCategory):
            with self.subTest(model=model.__name__):
                fields = {f.name: f for f in model._meta.get_fields()}
                self.assertEqual(set(fields) & {"name", "sort_order"}, {"name", "sort_order"})
                self.assertTrue(fields["name"].unique)
                obj = model.objects.create(name="测试项")
                self.assertEqual(obj.sort_order, 0)
                self.assertEqual(list(model.objects.values_list("name", flat=True)), ["测试项"])

    def test_vocabulary_name_unique(self):
        Discipline.objects.create(name="计算机科学")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Discipline.objects.create(name="计算机科学")


class FeaturedItemTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = make_department("教务处", "jwc")

    def test_end_before_start_rejected(self):
        item = FeaturedItem(
            start_at=dt.datetime(2026, 9, 2, tzinfo=UTC),
            end_at=dt.datetime(2026, 9, 1, tzinfo=UTC),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("不得早于开始时间", str(ctx.exception))

    def test_end_equal_start_legal(self):
        same = dt.datetime(2026, 9, 1, tzinfo=UTC)
        item = FeaturedItem(start_at=same, end_at=same)
        item.clean()  # 不抛即合法

    def test_enabled_default_true(self):
        self.assertTrue(FeaturedItem().enabled)

    def test_chooser_targets_exactly_five_content_types(self):
        """§13.3：选择器过滤仅五类内容页（容器/板块/首页不可选）。"""
        from departments.models import DepartmentContainerPage
        from home.models import HomePage, SectionPage

        chooser = None
        for panel in FeaturedItem.panels:
            widget = getattr(panel, "widget", None)
            if isinstance(widget, AdminPageChooser):
                chooser = widget
        self.assertIsNotNone(chooser, "panels 须含 AdminPageChooser")
        self.assertEqual(
            set(chooser.target_models),
            {NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage},
        )
        for excluded in (HomePage, SectionPage, DepartmentContainerPage):
            self.assertNotIn(excluded, chooser.target_models)


class SiteSettingsTests(TestCase):
    def test_feedback_email_required(self):
        with self.assertRaises(ValidationError) as ctx:
            SiteSettings().full_clean()
        self.assertIn("feedback_email", ctx.exception.message_dict)

    def test_feedback_email_validated(self):
        with self.assertRaises(ValidationError) as ctx:
            SiteSettings(feedback_email="not-an-email").full_clean()
        self.assertIn("feedback_email", ctx.exception.message_dict)

    def test_alert_window_pairing(self):
        start = dt.datetime(2026, 9, 1, tzinfo=UTC)
        end = dt.datetime(2026, 9, 2, tzinfo=UTC)
        # 同时填（止≥起）与同时空均合法。
        SiteSettings(feedback_email="f@e.com", alert_start_at=start, alert_end_at=end).clean()
        SiteSettings(feedback_email="f@e.com").clean()
        # 只填一端 → 拒。
        with self.assertRaises(ValidationError) as ctx:
            SiteSettings(feedback_email="f@e.com", alert_start_at=start).clean()
        self.assertIn("同时填写或同时留空", str(ctx.exception))

    def test_alert_end_before_start_rejected(self):
        start = dt.datetime(2026, 9, 2, tzinfo=UTC)
        end = dt.datetime(2026, 9, 1, tzinfo=UTC)
        with self.assertRaises(ValidationError) as ctx:
            SiteSettings(feedback_email="f@e.com", alert_start_at=start, alert_end_at=end).clean()
        self.assertIn("不得早于起", str(ctx.exception))


class MigrationZeroDriftTests(TestCase):
    def test_makemigrations_reports_no_changes(self):
        """模型与迁移零漂移（任务批令自测项，实测非声明）。"""
        from io import StringIO

        out = StringIO()
        call_command("makemigrations", "--check", "--dry-run", stdout=out)
        self.assertIn("No changes detected", out.getvalue())
