"""A3.1 学习资料/软件工具双页模型测试（CONTENT_MODEL §8/§9）。

- MaterialPage：受控三维（学科 FK/资料类型 FK/词表标签）＋摘要必填、
  外链/附件可选（§8.1；CM-04 外链可选）；无图片/有效期字段；
- SoftwareToolPage：六项齐备（§9.1），platforms ≥1 双闸
  （blank=False 表单必填＋clean 模型兜底）、source_url/license_note 必填、
  无附件块/无摘要字段；
- 两页字段形状与设计逐项对齐（§8.1 vs §9.1 分叉留痕）。
"""

import datetime as dt

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from resources.models import Discipline, MaterialPage, MaterialType, Platform, SoftwareToolPage

from .helpers import build_sections, make_container, make_department, make_image, make_material

UTC = dt.UTC


def _body_value(text):
    """Draftail contentstate JSON 表单值（与 tests.helpers 同格式，行内短写）。"""
    return (
        '{"entityMap":{},"blocks":[{"key":"k","text":"' + text + '","type":"unstyled",'
        '"depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}]}'
    )


class MaterialSoftwareBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("图书馆", "lib")
        cls.materials_container = make_container(sections["materials"], cls.department)
        cls.software_department = make_department("教务处", "jwc")
        cls.software_container = make_container(sections["software"], cls.software_department)

    def material_data(self, **overrides):
        # get_or_create：同方法多 subTest 复用词表项（词表名唯一）。
        discipline = Discipline.objects.get_or_create(name="计算机科学")[0]
        material_type = MaterialType.objects.get_or_create(name="课件")[0]
        data = {
            "title": "测试资料",
            "slug": "test-material",
            "summary": "测试摘要",
            "department": str(self.materials_container.department_id),
            "discipline": str(discipline.pk),
            "material_type": str(material_type.pk),
            "body-count": "1",
            "body-0-deleted": "",
            "body-0-order": "0",
            "body-0-type": "paragraph",
            "body-0-value": _body_value("正文"),
        }
        data.update(overrides)
        return data

    def software_data(self, **overrides):
        platforms = [Platform.objects.get_or_create(name="Windows")[0]]
        data = {
            "title": "测试工具",
            "slug": "test-tool",
            "department": str(self.software_container.department_id),
            "platforms": [str(p.pk) for p in platforms],
            "source_url": "https://example.com/tool",
            "license_note": "校园授权，免费使用",
            "body-count": "1",
            "body-0-deleted": "",
            "body-0-order": "0",
            "body-0-type": "paragraph",
            "body-0-value": _body_value("用途"),
        }
        data.update(overrides)
        return data


class MaterialFieldShapeTests(MaterialSoftwareBase):
    """§8.1 字段位反射：资料侧声明与"无字段声明"。"""

    def test_material_fields(self):
        fields = {f.name: f for f in MaterialPage._meta.get_fields()}
        for name in (
            "summary",
            "body",
            "discipline",
            "material_type",
            "external_url",
            "attachments",
            "department",
            "tags",
        ):
            self.assertIn(name, fields)
        # §8.1 无字段声明：无图片、无 license/source/平台（软件侧专属）。
        # expire_at 属 Page 基类固有字段（有效期语义仅经 clean 施加于 Notice）。
        for absent in ("image", "source_url", "license_note", "platforms"):
            self.assertNotIn(absent, fields, f"MaterialPage 不应有 {absent}（§8.1）")

    def test_material_optional_fields(self):
        fields = {f.name: f for f in MaterialPage._meta.get_fields()}
        self.assertTrue(fields["external_url"].blank)  # CM-04：外链可选
        self.assertTrue(fields["attachments"].blank)
        self.assertFalse(fields["summary"].blank)
        self.assertFalse(fields["discipline"].blank)  # 受控三维权必填
        self.assertFalse(fields["material_type"].blank)

    def test_material_fk_protect_vocabularies(self):
        """词表 FK 均为 PROTECT（词表被引用不可删；删除政策 DEFERRED_TO_M3_3）。"""
        fields = {f.name: f for f in MaterialPage._meta.get_fields()}
        self.assertEqual(fields["discipline"].remote_field.on_delete.__name__, "PROTECT")
        self.assertEqual(fields["material_type"].remote_field.on_delete.__name__, "PROTECT")


class MaterialFormTests(MaterialSoftwareBase):
    def test_required_fk_missing_rejected(self):
        for field in ("discipline", "material_type", "summary"):
            with self.subTest(field=field):
                data = self.material_data(**{field: ""})
                form = MaterialPage.get_edit_handler().get_form_class()(
                    data=data, parent_page=self.materials_container
                )
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_external_url_optional(self):
        form = MaterialPage.get_edit_handler().get_form_class()(
            data=self.material_data(external_url=""), parent_page=self.materials_container
        )
        self.assertTrue(form.is_valid(), form.errors)


class SoftwareFieldShapeTests(MaterialSoftwareBase):
    """§9.1 六项齐备、无摘要/附件。"""

    def test_software_fields(self):
        fields = {f.name: f for f in SoftwareToolPage._meta.get_fields()}
        for name in ("body", "platforms", "source_url", "license_note", "department"):
            self.assertIn(name, fields)
        # §9.1 无字段声明：无摘要、无图片、无附件字段（不托管安装包）。
        for absent in ("summary", "image", "attachments", "external_url", "tags"):
            self.assertNotIn(absent, fields, f"SoftwareToolPage 不应有 {absent}（§9.1）")

    def test_software_required_fields(self):
        fields = {f.name: f for f in SoftwareToolPage._meta.get_fields()}
        self.assertFalse(fields["source_url"].blank)
        self.assertFalse(fields["license_note"].blank)
        self.assertFalse(fields["platforms"].blank)


class SoftwarePlatformGatesTests(MaterialSoftwareBase):
    """§9.2：platforms ≥1 双闸。"""

    def test_form_gate_missing_platforms_rejected(self):
        """表单闸：blank=False → ModelMultipleChoiceField 必填。"""
        form = SoftwareToolPage.get_edit_handler().get_form_class()(
            data=self.software_data(platforms=[]), parent_page=self.software_container
        )
        self.assertFalse(form.is_valid())
        self.assertIn("platforms", form.errors)

    def test_model_gate_empty_cluster_rejected(self):
        """模型闸：cluster 内存值已就位且为空 → clean 拒（模型直建路径）。"""
        page = SoftwareToolPage(
            title="无平台工具",
            slug="no-platform",
            body=[("paragraph", "<p>用途</p>")],
            department=self.software_department,
            source_url="https://example.com/t",
            license_note="免费",
        )
        page.platforms = []  # 显式空集：cluster 内存值就位
        page._provisional_parent = self.software_container
        with self.assertRaises(ValidationError) as ctx:
            page.clean()
        self.assertIn("适用平台至少选择一项", str(ctx.exception))

    def test_model_gate_form_flow_with_selection_not_falsely_rejected(self):
        """表单流选中平台后不被 clean 误拒（M2M 回填时序，§9.2 实测口径）。"""
        form = SoftwareToolPage.get_edit_handler().get_form_class()(
            data=self.software_data(), parent_page=self.software_container
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_model_gate_with_platforms_accepted(self):
        platform = Platform.objects.create(name="Linux")
        page = SoftwareToolPage(
            title="有平台工具",
            slug="with-platform",
            body=[("paragraph", "<p>用途</p>")],
            department=self.software_department,
            source_url="https://example.com/t",
            license_note="免费",
        )
        page.platforms = [platform]
        page._provisional_parent = self.software_container
        page.clean()  # 不抛即合法


class SoftwareFormTests(MaterialSoftwareBase):
    def test_source_url_required_and_validated(self):
        for value in ("", "不是网址"):
            with self.subTest(value=value):
                form = SoftwareToolPage.get_edit_handler().get_form_class()(
                    data=self.software_data(source_url=value),
                    parent_page=self.software_container,
                )
                self.assertFalse(form.is_valid())
                self.assertIn("source_url", form.errors)

    def test_license_note_required(self):
        form = SoftwareToolPage.get_edit_handler().get_form_class()(
            data=self.software_data(license_note=""), parent_page=self.software_container
        )
        self.assertFalse(form.is_valid())
        self.assertIn("license_note", form.errors)


class CoverImageTests(MaterialSoftwareBase):
    """轮播封面图（CoverImageMixin，首页升级 Phase 3）：资料/工具两页新增可空字段。"""

    def test_cover_image_field_shape(self):
        """可空/blank、Image FK、SET_NULL、related_name='+'、软提示 help_text。"""
        for model in (MaterialPage, SoftwareToolPage):
            field = model._meta.get_field("cover_image")
            self.assertTrue(field.null and field.blank)
            self.assertEqual(field.remote_field.model._meta.label, "wagtailimages.Image")
            self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
            self.assertEqual(field.remote_field.related_name, "+")
            self.assertEqual(field.help_text, "推荐尺寸 1600×600（8:3）")

    def test_cover_image_delete_sets_null_page_kept(self):
        cover = make_image("资料轮播封面")
        material = make_material(self.materials_container, slug="cover-setnull", publish=True)
        material.cover_image = cover
        material.save()
        cover.delete()
        material.refresh_from_db()
        self.assertIsNone(material.cover_image)
        self.assertTrue(MaterialPage.objects.filter(pk=material.pk).exists())
