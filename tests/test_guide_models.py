"""A3.1 校园指南页模型测试（CONTENT_MODEL §10；PRD §7.6 九字段）。

- 九字段一字不差：必填集八项＋补充说明唯一可选；
- 维护方式两选项逐源 PRD 原文；
- 无 StreamField/图片/附件/外链/标签字段（§10.1 无字段声明）；
- last_confirmed_on 为显式业务日期（非自动时间戳，CM-06）。
"""

from django.test import TestCase
from guides.models import GuideCategory, GuidePage
from wagtail.fields import StreamField

from .helpers import build_sections, make_container, make_department

NINE_FIELDS = [
    "title",  # #1 服务名称（title 映射，不双轨命名）
    "category",  # #2 指南类别
    "location",  # #3 地点
    "opening_hours",  # #4 开放时间
    "contact",  # #5 联系方式
    "extra_notes",  # #6 补充说明（唯一可选）
    "responsible_party",  # #7 责任来源或责任单位
    "maintenance_mode",  # #8 维护方式
    "last_confirmed_on",  # #9 最后确认日期或更新时间
]


class GuideBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("后勤处", "houqin")
        cls.container = make_container(sections["guide"], cls.department)

    def guide_data(self, **overrides):
        # get_or_create：同方法多 subTest 复用类别（词表名唯一）。
        category = GuideCategory.objects.get_or_create(name="食堂")[0]
        data = {
            "title": "测试指南",
            "slug": "test-guide",
            "department": str(self.container.department_id),
            "category": str(category.pk),
            "location": "一食堂二楼",
            "opening_hours": "周一至周五 7:00-19:00",
            "contact": "电话 0000-0000",
            "responsible_party": "后勤处",
            "maintenance_mode": "self",
            "last_confirmed_on": "2026-08-01",
        }
        data.update(overrides)
        return data


class GuideNineFieldsTests(GuideBase):
    """CM-06：九字段一字不差、一个不删。"""

    def test_nine_fields_present(self):
        fields = {f.name: f for f in GuidePage._meta.get_fields()}
        for name in NINE_FIELDS:
            self.assertIn(name, fields, f"九字段缺 {name}（PRD §7.6 一字不差）")

    def test_extra_notes_is_the_only_optional_one(self):
        fields = {f.name: f for f in GuidePage._meta.get_fields()}
        for name in NINE_FIELDS:
            if name == "title":
                continue  # title 由 Page 承载（必填属 Wagtail 基线）
            expected_blank = name == "extra_notes"
            self.assertEqual(
                fields[name].blank,
                expected_blank,
                f"{name} 可选性应为 {expected_blank}（§10.1）",
            )

    def test_no_undeclared_content_fields(self):
        """§10.1 无字段声明：无正文流/图片/附件/外链/标签/活动字段。
        （expire_at 属 Wagtail Page 基类固有字段，不在"无声明"排除之列。）"""
        fields = {f.name: f for f in GuidePage._meta.get_fields()}
        for absent in (
            "body",
            "image",
            "attachments",
            "external_url",
            "tags",
            "summary",
            "event_start_at",
            "event_location",
        ):
            self.assertNotIn(absent, fields, f"GuidePage 不应有 {absent}（§10.1）")

    def test_no_streamfield_at_all(self):
        for field in GuidePage._meta.get_fields():
            self.assertNotIsInstance(field, StreamField)

    def test_maintenance_mode_choices_verbatim(self):
        """#8 两选项逐源 PRD 原文（§10.1 冻结）。"""
        fields = {f.name: f for f in GuidePage._meta.get_fields()}
        self.assertEqual(
            dict(fields["maintenance_mode"].choices),
            {
                "self": "责任部门后台自维护",
                "curated": "统一邮箱投稿·总管理员代维护",
            },
        )

    def test_last_confirmed_on_is_explicit_business_date(self):
        """#9 显式业务日期承载人工确认语义，非自动时间戳（CM-06）。"""
        from django.db.models import DateField

        field = {f.name: f for f in GuidePage._meta.get_fields()}["last_confirmed_on"]
        self.assertIsInstance(field, DateField)
        self.assertFalse(field.auto_now)
        self.assertFalse(field.auto_now_add)

    def test_category_fk_protect(self):
        field = {f.name: f for f in GuidePage._meta.get_fields()}["category"]
        self.assertEqual(field.remote_field.on_delete.__name__, "PROTECT")


class GuideFormTests(GuideBase):
    def test_each_required_field_missing_rejected(self):
        for field in NINE_FIELDS:
            if field in ("title", "extra_notes"):
                continue
            with self.subTest(field=field):
                form = GuidePage.get_edit_handler().get_form_class()(
                    data=self.guide_data(**{field: ""}), parent_page=self.container
                )
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_extra_notes_optional(self):
        form = GuidePage.get_edit_handler().get_form_class()(
            data=self.guide_data(extra_notes=""), parent_page=self.container
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_maintenance_mode_invalid_choice_rejected(self):
        form = GuidePage.get_edit_handler().get_form_class()(
            data=self.guide_data(maintenance_mode="volunteer"),
            parent_page=self.container,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("maintenance_mode", form.errors)
