"""A3.2（M3.3）五状态推导测试（CONTENT_MODEL §14.2；PS-15/16 推导半边）。

零新增字段（§14.1）：状态＝内建列纯推导（S0–S4 常量），仅五类内容页
混入 ``LifecycleStateMixin``，结构页/受控数据不适用。S1 挂钩修订级
``approved_go_live_at`` 待执行修订；对象级 ``go_live_at`` 残留三序列
（§14.2 注记）逐一覆盖——残留不得把 S3/S4 误判为 S1。
"""

import datetime as dt

from django.db import models
from django.test import TestCase
from django.utils import timezone
from guides.models import GuidePage
from home.models import FeaturedItem, HomePage, SectionPage, SiteSettings
from notices.lifecycle import (
    LIFECYCLE_DRAFT,
    LIFECYCLE_EXPIRED,
    LIFECYCLE_LIVE,
    LIFECYCLE_SCHEDULED,
    LIFECYCLE_UNPUBLISHED,
    LifecycleStateMixin,
    current_default_pages,
)
from notices.models import ArticlePage, NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from wagtail.models import Page

from .helpers import build_sections, future, make_container, make_department, make_notice

HOUR = dt.timedelta(hours=1)


class LifecycleBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(sections["chronicle"], cls.department)


class StateDerivationTests(LifecycleBase):
    """§14.2 五状态表逐行（优先级先命中先得）。"""

    def test_s0_draft_never_published(self):
        page = make_notice(self.container, slug="s0")
        self.assertFalse(page.live)
        self.assertIsNone(page.first_published_at)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_DRAFT)

    def test_s2_live_published(self):
        page = make_notice(self.container, slug="s2", publish=True)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)

    def test_s2a_s2b_substates_via_has_unpublished_changes(self):
        page = make_notice(self.container, slug="s2ab", publish=True)
        self.assertFalse(page.has_unpublished_changes)  # S2a：无未发布修订
        page.title = "修订标题"
        page.save_revision()
        page.refresh_from_db()
        self.assertTrue(page.has_unpublished_changes)  # S2b：编辑存草稿后
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)  # 仍 S2（E5 非转换）

    def test_s1_scheduled_pending_revision(self):
        page = make_notice(self.container, slug="s1", schedule_at=future(days=1))
        self.assertIsNotNone(page.scheduled_revision)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)

    def test_s3_expired_via_task(self):
        page = make_notice(self.container, slug="s3", publish=True)
        NoticePage.objects.filter(pk=page.pk).update(expire_at=timezone.now() - HOUR)
        from django.core.management import call_command

        call_command("publish_scheduled", verbosity=0)
        page.refresh_from_db()
        self.assertTrue(page.expired)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_EXPIRED)

    def test_s4_unpublished_manual(self):
        page = make_notice(self.container, slug="s4", publish=True)
        page.unpublish()
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_UNPUBLISHED)

    def test_all_five_models_derive(self):
        """§14.1 适用对象＝五类内容页：Mixin 全体继承且可推导（live 态抽测）。"""
        from .helpers import make_article, make_guide, make_material, make_software

        sections = {s.slug: s for s in SectionPage.objects.all()}
        article = make_article(self.container, slug="st-article", publish=True)
        materials_container = make_container(sections["materials"], self.department)
        material = make_material(materials_container, slug="st-material", publish=True)
        software_container = make_container(sections["software"], self.department)
        software = make_software(software_container, slug="st-software", publish=True)
        guide_container = make_container(sections["guide"], self.department)
        guide = make_guide(guide_container, slug="st-guide", publish=True)
        for page in (article, material, software, guide):
            self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)


class ResidualGoLiveAtTests(LifecycleBase):
    """§14.2 S1 判定注记：对象级 go_live_at 残留三序列（E3/E7/E8 不清对象级）。"""

    def _residual_live_page(self, slug):
        """预约→到点发布：对象级 go_live_at 残留过去值，状态须为 S2。"""
        from unittest import mock

        page = make_notice(self.container, slug=slug, schedule_at=timezone.now() + HOUR)
        later = timezone.now() + 2 * HOUR
        with mock.patch("django.utils.timezone.now", return_value=later):
            from django.core.management import call_command

            call_command("publish_scheduled", verbosity=0)
        page.refresh_from_db()
        self.assertIsNotNone(page.go_live_at)  # 残留未清（E3 不清对象级）
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)  # PS-16：仍 S2
        return page

    def test_residual_then_unpublish_is_s4_not_s1(self):
        page = self._residual_live_page("res-s4")
        page.unpublish()
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_UNPUBLISHED)

    def test_residual_then_expire_is_s3_not_s1(self):
        page = self._residual_live_page("res-s3")
        NoticePage.objects.filter(pk=page.pk).update(expire_at=timezone.now() - HOUR)
        from django.core.management import call_command

        call_command("publish_scheduled", verbosity=0)
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_EXPIRED)

    def test_draft_with_go_live_at_unpublished_revision_is_not_s1(self):
        """仅存草稿＋填预约未点发布：对象列已持久化、修订级未登记→判 S0/S4
        （PS-15 后半）。对象列持久化＝编辑表单保存路径（page.save 全列写入；
        save_revision 仅更新有限列，亲证 wagtail/models/pages.py）。"""
        page = make_notice(self.container, slug="res-s0")
        page.go_live_at = future(days=1)
        page.save()  # 表单保存：对象列持久化
        page.save_revision()  # 存草稿：修订级未登记（approved_go_live_at 空）
        page.refresh_from_db()
        self.assertIsNotNone(page.go_live_at)
        self.assertIsNone(page.scheduled_revision)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_DRAFT)
        page.go_live_at = None  # 清预约位、存新修订（内容无预约）→E1→E8
        page.save()
        page.publish(page.save_revision())
        page.refresh_from_db()  # 发布动作改写的是修订重建实例，本实例须重读
        page.unpublish()
        page.go_live_at = future(days=2)
        page.save()
        page.save_revision()
        page.refresh_from_db()
        self.assertIsNotNone(page.go_live_at)
        self.assertIsNone(page.scheduled_revision)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_UNPUBLISHED)


class MachineShapeTests(LifecycleBase):
    """§14.1 载体事实：零新增字段、仅五类内容页适用。"""

    def test_mixin_declares_no_model_fields(self):
        for value in vars(LifecycleStateMixin).values():
            self.assertNotIsInstance(value, models.Field)

    def test_mixin_only_on_five_content_pages(self):
        for model in (NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage):
            self.assertTrue(issubclass(model, LifecycleStateMixin))
        for model in (HomePage, SectionPage, Page, FeaturedItem, SiteSettings):
            self.assertFalse(issubclass(model, LifecycleStateMixin))

    def test_in_current_default_membership(self):
        """§16.4 CURRENT_DEFAULT 成员＝S2 恰一类（in_current_default 直读）。"""
        live = make_notice(self.container, slug="cd-live", publish=True)
        draft = make_notice(self.container, slug="cd-draft")
        scheduled = make_notice(self.container, slug="cd-sch", schedule_at=future(days=1))
        expired = make_notice(self.container, slug="cd-exp", publish=True)
        NoticePage.objects.filter(pk=expired.pk).update(expire_at=timezone.now() - HOUR)
        from django.core.management import call_command

        call_command("publish_scheduled", verbosity=0)
        expired.refresh_from_db()
        unpublished = make_notice(self.container, slug="cd-unpub", publish=True)
        unpublished.unpublish()
        unpublished.refresh_from_db()
        self.assertTrue(live.in_current_default)
        for page in (draft, scheduled, expired, unpublished):
            self.assertFalse(page.in_current_default)

    def test_current_default_queryset_excludes_non_live(self):
        make_notice(self.container, slug="qs-live", publish=True)
        make_notice(self.container, slug="qs-draft")
        make_notice(self.container, slug="qs-sch", schedule_at=future(days=1))
        expired = make_notice(self.container, slug="qs-exp", publish=True)
        NoticePage.objects.filter(pk=expired.pk).update(expire_at=timezone.now() - HOUR)
        from django.core.management import call_command

        call_command("publish_scheduled", verbosity=0)
        slugs = set(current_default_pages().values_list("slug", flat=True))
        self.assertIn("qs-live", slugs)
        self.assertNotIn("qs-draft", slugs)
        self.assertNotIn("qs-sch", slugs)
        self.assertNotIn("qs-exp", slugs)
