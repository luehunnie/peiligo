"""A3.1 通知/文章双页模型测试（CONTENT_MODEL §5/§6；CM-01）。

- 有效期语义独立：Notice 必填 expire_at、Article 可选（PRD §7.1/§7.2 分叉），
  且该必填性由 clean 施加（复用 Wagtail Page 自身字段，语义独立于发布工作流，
  到期行为 DEFERRED_TO_M3_3）；
- 必填/可选字段全清单（§5.1/§6.1 同构，仅有效期分叉）；
- body min_num=1（空正文拒）；
- 外链 URLField 校验。
"""

import datetime as dt

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from notices.models import ArticlePage, NoticePage

from .helpers import (
    article_data,
    build_sections,
    make_container,
    make_department,
    make_image,
    make_notice,
    notice_data,
)

UTC = dt.UTC

# 两类型业务字段集（§5.1/§6.1 完全同构；仅 expire_at 必填性分叉）。
SHARED_BUSINESS_FIELDS = {
    "summary",
    "body",
    "department",
    "image",
    "attachments",
    "external_url",
    "tags",
    "event_start_at",
    "event_end_at",
    "event_location",
    "event_is_online",
    "event_registration_url",
}


class NoticeArticleBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(sections["chronicle"], cls.department)


class FieldShapeTests(NoticeArticleBase):
    """字段位与必填性反射（§5.1/§6.1）。"""

    def test_shared_business_field_sets_identical(self):
        for model in (NoticePage, ArticlePage):
            own = {f.name for f in model._meta.get_fields() if f.name in SHARED_BUSINESS_FIELDS}
            self.assertEqual(own, SHARED_BUSINESS_FIELDS)

    def test_optional_fields_declared_optional(self):
        for model in (NoticePage, ArticlePage):
            fields = {f.name: f for f in model._meta.get_fields()}
            self.assertTrue(fields["image"].null and fields["image"].blank)
            self.assertTrue(fields["attachments"].blank)
            self.assertTrue(fields["external_url"].blank)
            self.assertFalse(fields["summary"].blank)
            # expire_at 是 Page 基类字段（blank=True），必填性由 clean 分叉施加。
            self.assertTrue(fields["expire_at"].blank)

    def test_allowed_sections_both_chronicle_and_events(self):
        self.assertEqual(NoticePage.ALLOWED_SECTIONS, {"chronicle", "events"})
        self.assertEqual(ArticlePage.ALLOWED_SECTIONS, {"chronicle", "events"})


class ExpireAtSemanticsTests(NoticeArticleBase):
    """CM-01：有效期必填性分叉——Notice 独有必填语义。"""

    def test_notice_without_expire_rejected(self):
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container, expire_at=""), parent_page=self.container
        )
        self.assertFalse(form.is_valid())
        self.assertIn("通知必须填写有效期", str(form.errors))

    def test_notice_with_expire_accepted(self):
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container), parent_page=self.container
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_article_without_expire_accepted(self):
        """文章有效期可选：留空合法（PRD §7.2"不默认设置下线时间"）。"""
        form = ArticlePage.get_edit_handler().get_form_class()(
            data=article_data(self.container, expire_at=""), parent_page=self.container
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_model_level_notice_expire_required(self):
        notice = NoticePage(
            title="无有效期通知",
            slug="no-expire",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=self.department,
        )
        notice._provisional_parent = self.container
        with self.assertRaises(ValidationError) as ctx:
            notice.clean()
        self.assertIn("有效期", str(ctx.exception))

    def test_expire_uses_wagtail_page_own_field_no_extra_field(self):
        """语义独立＝复用 Page 自身 expire_at，不另设字段（§5.2）。"""
        for model in (NoticePage, ArticlePage):
            fields = {f.name: f for f in model._meta.get_fields()}
            self.assertNotIn("valid_until", fields)
            self.assertNotIn("notice_expire_at", fields)


class RequiredOptionalFormTests(NoticeArticleBase):
    """必填/可选与校验（表单流全链）。"""

    def test_summary_required(self):
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container, summary=""), parent_page=self.container
        )
        self.assertFalse(form.is_valid())
        self.assertIn("summary", form.errors)

    def test_body_min_one_block(self):
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(
                self.container,
                **{
                    "body-count": "0",
                },
            ),
            parent_page=self.container,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_external_url_optional_and_validated(self):
        ok = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container, external_url=""),
            parent_page=self.container,
        )
        self.assertTrue(ok.is_valid(), ok.errors)
        bad = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container, external_url="不是网址"),
            parent_page=self.container,
        )
        self.assertFalse(bad.is_valid())
        self.assertIn("external_url", bad.errors)

    def test_article_summary_required_too(self):
        form = ArticlePage.get_edit_handler().get_form_class()(
            data=article_data(self.container, summary=""), parent_page=self.container
        )
        self.assertFalse(form.is_valid())
        self.assertIn("summary", form.errors)

    def test_notice_and_article_are_distinct_page_types(self):
        """独立 Page 类型不混用（PRD §7.2 末句；ADR-0005 #1/#2）。"""
        self.assertNotEqual(NoticePage, ArticlePage)
        self.assertFalse(issubclass(NoticePage, ArticlePage))
        self.assertFalse(issubclass(ArticlePage, NoticePage))


class CoverImageTests(NoticeArticleBase):
    """轮播封面图（CoverImageMixin，首页升级 Phase 3）：与既有 image 独立共存。"""

    def test_cover_image_field_shape(self):
        """可空/blank、Image FK、SET_NULL、related_name='+'、软提示 help_text。"""
        for model in (NoticePage, ArticlePage):
            field = model._meta.get_field("cover_image")
            self.assertTrue(field.null and field.blank)
            self.assertEqual(field.remote_field.model._meta.label, "wagtailimages.Image")
            self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
            self.assertEqual(field.remote_field.related_name, "+")
            self.assertEqual(field.help_text, "推荐尺寸 1600×600（8:3）")

    def test_image_and_cover_image_coexist(self):
        """既有 image（正文插图）与 cover_image（轮播封面）同时存在互不影响。"""
        illustration = make_image("正文插图")
        cover = make_image("轮播封面")
        notice = make_notice(self.container, slug="cover-coexist", publish=True)
        notice.image = illustration
        notice.cover_image = cover
        notice.save()
        notice.refresh_from_db()
        self.assertEqual(notice.image, illustration)
        self.assertEqual(notice.cover_image, cover)

    def test_cover_image_delete_sets_null_page_kept(self):
        cover = make_image("轮播封面")
        notice = make_notice(self.container, slug="cover-setnull", publish=True)
        notice.cover_image = cover
        notice.save()
        cover.delete()
        notice.refresh_from_db()
        self.assertIsNone(notice.cover_image)
        self.assertTrue(NoticePage.objects.filter(pk=notice.pk).exists())
