"""A3.2（M3.3）状态转换测试（CONTENT_MODEL §14.3；PS-10/14/16/17/18/21）。

E1–E11 全边逐一走通＋非法转换闭集反例逐条证伪（PS-21）。操作等价路径：
立即发布/重发布＝``save_revision().publish()``；预约＝保存携带未来
``go_live_at`` 的修订后 ``publish()``；到点＝``publish_scheduled`` 命令
（时间经 mock 推进）；下线＝``unpublish()``。发布动作改写修订重建实例、
``scheduled_revision`` 缓存不随 refresh 失效——动作后取新实例再断言。
"""

import datetime as dt
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from notices.lifecycle import (
    LIFECYCLE_DRAFT,
    LIFECYCLE_EXPIRED,
    LIFECYCLE_LIVE,
    LIFECYCLE_SCHEDULED,
    LIFECYCLE_UNPUBLISHED,
)
from notices.models import NoticePage
from wagtail.models import Revision

from .helpers import build_sections, future, make_container, make_department, make_notice

HOUR = dt.timedelta(hours=1)


def run_publish_scheduled_at(later):
    """以推进后的当前时刻执行 publish_scheduled（E3/E7 到点语义）。"""
    with mock.patch("django.utils.timezone.now", return_value=later):
        call_command("publish_scheduled", verbosity=0)


def backdate_expiry(page):
    """对象级 expire_at 回拨到过去（绕开 clean 的 §16.2 未来性，模拟时间流逝）。"""
    NoticePage.objects.filter(pk=page.pk).update(expire_at=timezone.now() - HOUR)


class TransitionBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(sections["chronicle"], cls.department)

    def _schedule(self, slug, hours=1):
        """E2：存未来 go_live_at 并发布→S1。"""
        page = make_notice(
            self.container, slug=slug, schedule_at=timezone.now() + dt.timedelta(hours=hours)
        )
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)
        return page

    def _expired(self, slug):
        """E7：发布→对象级回拨→任务执行→S3。"""
        page = make_notice(self.container, slug=slug, publish=True)
        backdate_expiry(page)
        run_publish_scheduled_at(timezone.now() + HOUR)
        page.refresh_from_db()
        return page

    def _e11_reschedule(self, page):
        """E11：离线页携未来 go_live_at 重预约→S1（§16.2 新有效期先行）。"""
        page.go_live_at = future(days=1)
        page.publish(page.save_revision())
        page = NoticePage.objects.get(pk=page.pk)  # cached_property 须新实例
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)
        return page

    def _unschedule(self, page):
        """E4：解除待执行修订（仅清修订级 approved_go_live_at）。"""
        Revision.objects.filter(pk=page.scheduled_revision.pk).update(approved_go_live_at=None)
        return NoticePage.objects.get(pk=page.pk)


class LegalEdgeTests(TransitionBase):
    """E1–E11 合法边（每边一测；E5/E6 归 PS-11 侧 test_revisions）。"""

    def test_e1_draft_to_live_immediate(self):
        page = make_notice(self.container, slug="e1", publish=True)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)
        self.assertIsNotNone(page.first_published_at)

    def test_e2_draft_to_scheduled(self):
        self._schedule("e2")

    def test_e3_scheduled_to_live_via_task(self):
        page = self._schedule("e3")
        run_publish_scheduled_at(timezone.now() + 2 * HOUR)
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)

    def test_e3_not_due_stays_scheduled(self):
        page = self._schedule("e3-nd")
        run_publish_scheduled_at(timezone.now() + dt.timedelta(minutes=30))
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)

    def test_e4_unschedule_falls_back_to_draft(self):
        self.assertEqual(self._unschedule(self._schedule("e4-d")).lifecycle_state, LIFECYCLE_DRAFT)

    def test_e4_unschedule_falls_back_to_unpublished(self):
        page = make_notice(self.container, slug="e4-u", publish=True)
        page.unpublish()
        page.refresh_from_db()
        self.assertEqual(
            self._unschedule(self._e11_reschedule(page)).lifecycle_state, LIFECYCLE_UNPUBLISHED
        )

    def test_e4_unschedule_after_reschedule_of_expired_lands_s4(self):
        """E11 重预约路径（A3.2 复审建议纳入 PS-17）：预约动作置 ``expired=F``
        （publish_revision.py L135 两分支共行），故 expired→E11→E4 取消后按
        §14.2 推导回落 S4 而非预约前 S3——7.4.2 既有口径留档观察不阻断。"""
        page = self._expired("e4-e")
        page.expire_at = future(days=7)  # §16.2：过期通知重预约须给新有效期
        self.assertEqual(
            self._unschedule(self._e11_reschedule(page)).lifecycle_state, LIFECYCLE_UNPUBLISHED
        )  # 非 S3

    def test_e4_unschedule_via_builtin_admin_view(self):
        """E4 机制实测留痕：7.4.2 内建 unschedule 动作（后台修订历史视图，
        仅清修订级 ``approved_go_live_at``，generic/models.py）。"""
        page = self._schedule("e4-view")
        admin = get_user_model().objects.create_superuser("admin-e4", "a@e4.test", "pw-e4")
        self.client.force_login(admin)
        revision = page.scheduled_revision
        response = self.client.post(
            reverse("wagtailadmin_pages:revisions_unschedule", args=[page.pk, revision.pk])
        )
        self.assertEqual(response.status_code, 302)
        page = NoticePage.objects.get(pk=page.pk)
        self.assertIsNone(page.scheduled_revision)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_DRAFT)

    def test_e7_live_to_expired_via_task(self):
        page = self._expired("e7")
        self.assertFalse(page.live)
        self.assertTrue(page.expired)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_EXPIRED)

    def test_e8_live_to_unpublished_manual(self):
        page = make_notice(self.container, slug="e8", publish=True)
        page.unpublish()
        page.refresh_from_db()
        self.assertFalse(page.live)
        self.assertFalse(page.expired)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_UNPUBLISHED)

    def test_e9_expired_to_live_republish_resets_expired(self):
        page = self._expired("e9")
        page.expire_at = future(days=7)  # §16.2：过期通知重发布须给新有效期
        page.publish(page.save_revision())
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)
        self.assertFalse(page.expired)

    def test_e10_unpublished_to_live_republish(self):
        page = make_notice(self.container, slug="e10", publish=True)
        page.unpublish()
        page.refresh_from_db()
        page.expire_at = future(days=7)
        page.publish(page.save_revision())
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)

    def test_e11_offline_to_scheduled(self):
        page = make_notice(self.container, slug="e11", publish=True)
        page.unpublish()
        page.refresh_from_db()
        self._e11_reschedule(page)  # 下线页重预约（过期半边见 e4-e 测试）


class IllegalEdgeTests(TransitionBase):
    """PS-10/PS-21：表外转换全称非法——显式反例逐条证伪（状态不变）。"""

    def test_draft_never_expires(self):
        page = make_notice(self.container, slug="il-de")
        backdate_expiry(page)
        run_publish_scheduled_at(timezone.now() + HOUR)
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_DRAFT)  # 到期任务仅处理 live 页

    def test_draft_never_unpublishes(self):
        page = make_notice(self.container, slug="il-du")
        page.unpublish()  # 仅对 live 页生效（UnpublishAction if object.live）
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_DRAFT)

    def test_scheduled_never_expires(self):
        # 预约点晚于任务执行时刻：隔离"到期仅 live 生效"半边（到点发布另见 E3）。
        page = self._schedule("il-se", hours=2)
        backdate_expiry(page)
        run_publish_scheduled_at(timezone.now() + HOUR)
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)

    def test_scheduled_never_unpublishes(self):
        page = self._schedule("il-su")
        page.unpublish()
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)

    def test_expired_never_unpublishes_again(self):
        page = self._expired("il-eu")
        page.unpublish()  # 已离线，无再下线边
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_EXPIRED)

    def test_no_edge_back_to_draft_first_published_at_persistent(self):
        """PS-14：first_published_at 落定后跨改版重发/下线/重发布持久不回退。"""
        page = make_notice(self.container, slug="il-fpa", publish=True)
        first_published_at = page.first_published_at
        page.title = "改版标题一"
        page.publish(page.save_revision())
        page.refresh_from_db()
        self.assertEqual(page.first_published_at, first_published_at)
        page.unpublish()
        page.refresh_from_db()
        page.title = "改版标题二"
        page.publish(page.save_revision())
        page.refresh_from_db()
        self.assertEqual(page.first_published_at, first_published_at)
        self.assertNotEqual(page.first_published_at, page.last_published_at)

    def test_live_has_no_edge_to_scheduled(self):
        """live→scheduled 不产生边：live 页携未来 go_live_at 发布仍恒为 S2
        （官方 live+scheduled 位点保留，§14.3 不另设校验）。"""
        page = make_notice(self.container, slug="il-ls", publish=True)
        page.go_live_at = future(days=1)
        page.publish(page.save_revision())
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)


class ExpiryTaskScopeTests(TransitionBase):
    """PS-18：到期仅经任务对 live 页生效（set_expired unpublish）。"""

    def test_expiry_only_via_task_not_manual_college(self):
        """到期动作留痕：任务执行的 unpublish 携 set_expired=True（区别 E8 手动）。"""
        page = self._expired("et-task")
        self.assertTrue(page.expired)  # E7 带 set_expired
        manual = make_notice(self.container, slug="et-manual", publish=True)
        manual.unpublish()
        manual.refresh_from_db()
        self.assertFalse(manual.expired)  # E8 手动下线不置 expired
