"""A3.1 受控标签三道闸测试（CONTENT_MODEL §12；CM-08）。

- 词表闸：Tag 仅 taggit 内建两枚字段，不自增字段；
- 校验闸（模型 clean）：未知标签（无 pk 或不在词表）在集群自动创建前拦截；
- 表单闸（编辑控件）：ControlledTagField＝词表多选框，自由字符串被
  ModelMultipleChoiceField 拒绝；
- through 模型三枚：Notice/Article/Material 各自 ParentalKey，tag FK 指受控 Tag。
"""

import django.forms as forms
from django.core.exceptions import ValidationError
from django.test import TestCase
from notices.forms import ControlledTagField
from notices.models import (
    ArticlePage,
    ArticleTag,
    ControlledTaggableManager,
    NoticePage,
    NoticeTag,
    Tag,
)
from resources.models import MaterialPage, MaterialTag
from taggit.models import ItemBase

from .helpers import build_sections, make_container, make_department, notice_data


class TagVocabularyTests(TestCase):
    def test_tag_has_only_taggit_builtin_fields(self):
        field_names = {f.name for f in Tag._meta.get_fields()}
        # taggit TagBase 内建：name/slug；受控词表不自增字段（§12）。
        self.assertTrue({"name", "slug"} <= field_names)
        self.assertNotIn("description", field_names)

    def test_through_models_point_to_controlled_tag(self):
        for through, page_model in (
            (NoticeTag, NoticePage),
            (ArticleTag, ArticlePage),
            (MaterialTag, MaterialPage),
        ):
            with self.subTest(through=through.__name__):
                self.assertTrue(issubclass(through, ItemBase))
                self.assertEqual(through.tag.field.remote_field.model, Tag)
                self.assertEqual(through.content_object.field.remote_field.model, page_model)
                self.assertEqual(
                    through.content_object.field.remote_field.on_delete.__name__,
                    "CASCADE",
                )


class TagValidationGateTests(TestCase):
    """校验闸：clean_controlled_tags 拦未知标签（模型直建路径）。"""

    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(sections["chronicle"], cls.department)
        cls.known_tag = Tag.objects.create(name="开学", slug="kaixue")

    def _notice(self, tags):
        page = NoticePage(
            title="标签测试",
            slug="tag-test",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=self.department,
        )
        page._provisional_parent = self.container
        # 模型直建路径：taggit 无 __set__ 描述符，构造器传 tags 会存裸 list；
        # 经 cluster 管理器 set 落 _cluster_related_objects（真实直建口径）。
        page.tags.set(list(tags))
        return page

    def test_unknown_tag_without_pk_rejected(self):
        """校验闸真实拦截面：cluster 内持有未保存 Tag 实例（无 pk）→ clean 拒。
        经 through 项直挂构造（modelcluster add 同款路径；自由字符串的防线
        是表单闸，见 TagFormGateTests）。"""
        page = self._notice(tags=[self.known_tag])
        page.tags.get_tagged_item_manager().add(NoticeTag(tag=Tag(name="未登记新词", slug="new")))
        with self.assertRaises(ValidationError) as ctx:
            page.clean()
        self.assertIn("不在受控词表", str(ctx.exception))

    def test_known_tags_accepted(self):
        """词表内标签通过校验闸（有效期另有错误也不牵连标签闸）。"""
        page = self._notice(tags=[self.known_tag])
        try:
            page.clean()
        except ValidationError as e:
            self.assertNotIn("tags", e.message_dict)

    def test_no_tags_accepted(self):
        """§5.1：受控标签可选（0..n）。"""
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container), parent_page=self.container
        )
        self.assertTrue(form.is_valid(), form.errors)


class TagFormGateTests(TestCase):
    """表单闸：编辑控件仅词表多选，自由字符串不可绕过。"""

    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(sections["chronicle"], cls.department)
        cls.tag_a = Tag.objects.create(name="开学", slug="kaixue")
        cls.tag_b = Tag.objects.create(name="考试", slug="kaoshi")

    def test_page_form_uses_controlled_field(self):
        for model in (NoticePage, ArticlePage):
            with self.subTest(model=model.__name__):
                form_cls = model.get_edit_handler().get_form_class()
                field = form_cls.base_fields["tags"]
                self.assertIsInstance(field, ControlledTagField)
                self.assertIsInstance(field.widget, forms.CheckboxSelectMultiple)
                self.assertFalse(field.required)

    def test_manager_formfield_returns_controlled_field(self):
        manager = ControlledTaggableManager(through=NoticeTag, blank=True)
        self.assertIsInstance(manager.formfield(), ControlledTagField)

    def test_free_string_rejected_by_form(self):
        """CM-08：自由字符串标签在字段校验层被拒（非事后治理）。"""
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container, tags="自由输入的标签"),
            parent_page=self.container,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("tags", form.errors)

    def test_unknown_pk_rejected_by_form(self):
        """不在词表中的 pk（捏造）同样被拒。"""
        fake_pk = str(10**9)  # 远超测试库序列，词表中必不存在
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container, tags=[fake_pk]), parent_page=self.container
        )
        self.assertFalse(form.is_valid())
        self.assertIn("tags", form.errors)

    def test_known_pks_accepted(self):
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container, tags=[str(self.tag_a.pk), str(self.tag_b.pk)]),
            parent_page=self.container,
        )
        self.assertTrue(form.is_valid(), form.errors)
