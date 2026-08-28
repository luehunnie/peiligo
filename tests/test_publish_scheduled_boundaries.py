"""M5.1 publish_scheduled 边界测试（PUBLISH_ARCHIVE_SCHEDULING §5.3 用例表
B01–B18＋附录 A 断言 PA-01..30；分级 A）。

实现约束（PA-30）：全程禁 sleep——时间推进一律 ``mock.patch`` 推进
``django.utils.timezone.now`` 后执行正式命令 ``publish_scheduled``，或经
``queryset.update`` 直设对象级时间模拟流逝（既有模式
test_lifecycle_transitions.py:33-42）。

PA 覆盖映射（本文件＋既有在案）：

- PA-01/02/03/04/05/25/28 → ``GoLiveBoundaryTests``（B01–B05）
- PA-06/07/08/09/10/11/24/26 → ``ExpireBoundaryTests``（B06–B11/B13）
- PA-12 → test_publish_window.py ``PairWindowTests``（clean 层全路径闸口）
- PA-13/14/20/21/22/27 → ``CommandBehaviorTests``（B14/B15）
- PA-15/16/17/18 → ``FeaturedBoundaryTests``（B16–B18）
- PA-19 → ``TimezoneInvariantTests``（§4.4④ 表示层等价）
- PA-23/30 → ``MachineGuardTests``（机器形状与测试实现约束）
- PA-29 → 既有 test_permissions_governance.py N06（M4 落实：部门侧推荐位
  列表/新建/删改全拒＋零库变更），本轮不重述
"""

import datetime as dt
import inspect
import pathlib
import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import get_resolver, reverse
from django.utils import timezone
from guides.models import GuidePage
from home.models import FeaturedItem, SiteSettings
from notices.lifecycle import (
    LIFECYCLE_DRAFT,
    LIFECYCLE_EXPIRED,
    LIFECYCLE_LIVE,
    LIFECYCLE_SCHEDULED,
    current_default_pages,
)
from notices.models import ArticlePage, NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from wagtail.models import DraftStateMixin, Page, Revision, Site

from .helpers import (
    build_sections,
    future,
    make_article,
    make_container,
    make_department,
    make_notice,
)

HOUR = dt.timedelta(hours=1)
MINUTE = dt.timedelta(minutes=1)
SECOND = dt.timedelta(seconds=1)


def run_publish_scheduled_at(later):
    """以推进后的当前时刻执行 publish_scheduled（E3/E7 到点语义）。"""
    with mock.patch("django.utils.timezone.now", return_value=later):
        call_command("publish_scheduled", verbosity=0)


def set_expire_at(page, when):
    """对象级 expire_at 直设（绕开 clean 的 §16.2 未来性，模拟时间流逝）。"""
    Page.objects.filter(pk=page.pk).update(expire_at=when)


def make_featured(page, *, start=None, end=None, enabled=True):
    """窗口默认覆盖当前时刻的 FeaturedItem（展示有效性判定用）。"""
    now = timezone.now()
    return FeaturedItem.objects.create(
        content=page,
        start_at=start if start is not None else now - HOUR,
        end_at=end if end is not None else now + dt.timedelta(days=7),
        enabled=enabled,
    )


def _collect_url_names(resolver, acc):
    """递归收集全部具名 URL（含 app 命名空间内层）。"""
    for pattern in resolver.url_patterns:
        if hasattr(pattern, "url_patterns"):
            _collect_url_names(pattern, acc)
        elif pattern.name:
            acc.add(pattern.name)


class BoundaryBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.section = build_sections()["chronicle"]
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.section, cls.department)


class GoLiveBoundaryTests(BoundaryBase):
    """go_live_at 侧边界（B01–B05；PA-01..05/25/28）。"""

    def test_b01_scheduled_invisible_until_due(self):
        """PA-01：S1 前台 404、不入任何列表；判定＝修订级待执行修订。"""
        page = make_notice(
            self.container, slug="b01", title="B01预约页", schedule_at=timezone.now() + HOUR
        )
        self.assertIsNotNone(page.scheduled_revision)  # 修订级判定依据
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)
        self.assertEqual(self.client.get(page.url).status_code, 404)  # 前台 404
        slugs = set(current_default_pages().values_list("slug", flat=True))
        self.assertNotIn("b01", slugs)  # 不入默认列表
        html = self.client.get(self.section.url).content.decode()
        self.assertNotIn("B01预约页", html)  # 不入板块列表

    def test_b02_exact_go_live_boundary_strict_less(self):
        """PA-02：``approved_go_live_at__lt`` 严格比较——N == T 的运行不发布，
        首次 N > T 的运行发布（"精确到点"留待下一周期）。"""
        due = timezone.now() + HOUR
        page = make_notice(self.container, slug="b02", schedule_at=due)
        run_publish_scheduled_at(due)  # N == T
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)
        run_publish_scheduled_at(due + SECOND)  # 首次 N > T
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)

    def test_b03_due_published_within_hour_window(self):
        """PA-03：E3 转 live、入 CURRENT_DEFAULT；到点→可见 ≤1 小时任务窗口
        （§1.6 验收口径；production 每小时周期归 B6）。"""
        due = timezone.now() + 20 * MINUTE
        page = make_notice(self.container, slug="b03", schedule_at=due)
        run_publish_scheduled_at(due + 30 * MINUTE)
        page.refresh_from_db()
        self.assertTrue(page.live)
        self.assertTrue(page.in_current_default)
        self.assertEqual(self.client.get(page.url).status_code, 200)

    def test_b04_reschedule_replaces_single_pending_revision(self):
        """PA-04/PA-28：改期＝旧待执行修订被排他清空、单一新时刻登记
        （单一待执行修订不变式）；生效以新值为准，无旧时刻泄漏。"""
        now = timezone.now()
        first, second = now + HOUR, now + 3 * HOUR
        page = make_notice(self.container, slug="b04", schedule_at=first)
        page.go_live_at = second  # 改晚（改早同机制：整体替换，无最小间隔约束）
        page.publish(page.save_revision())
        pending = Revision.objects.filter(object_id=page.pk, approved_go_live_at__isnull=False)
        self.assertEqual(pending.count(), 1)  # PA-28：至多一条非空
        self.assertEqual(pending.first().approved_go_live_at, second)
        run_publish_scheduled_at(first + 30 * MINUTE)  # 越过旧时刻、未到新时刻
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)  # 旧时刻不泄漏
        run_publish_scheduled_at(second + 5 * MINUTE)
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)

    def test_b05_builtin_unschedule_falls_back_with_residual(self):
        """PA-05：内建 unschedule 仅清修订级；对象级 go_live_at 残留无害
        （不误判 S1）；回落预约前原态（E4）。"""
        page = make_notice(self.container, slug="b05", schedule_at=timezone.now() + HOUR)
        admin = get_user_model().objects.create_superuser("b05-admin", "b05@test", "pw-b05")
        self.client.force_login(admin)
        response = self.client.post(
            reverse(
                "wagtailadmin_pages:revisions_unschedule",
                args=[page.pk, page.scheduled_revision.pk],
            )
        )
        self.assertEqual(response.status_code, 302)
        page = NoticePage.objects.get(pk=page.pk)
        self.assertIsNone(page.scheduled_revision)  # 仅清修订级
        self.assertIsNotNone(page.go_live_at)  # 对象级残留（官方不清）
        self.assertNotEqual(page.lifecycle_state, LIFECYCLE_SCHEDULED)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_DRAFT)  # 从未发布页回落 S0

    def test_pa25_live_page_scheduled_revision_no_interruption(self):
        """PA-25：live 页携未来 go_live_at publish 保持 live 不中断（S2b），
        到点后修订内容生效（无新状态）。"""
        page = make_notice(self.container, slug="pa25", title="PA25原标题", publish=True)
        self.assertEqual(self.client.get(page.url).status_code, 200)
        due = timezone.now() + HOUR
        page.title = "PA25改版标题"
        page.go_live_at = due
        page.publish(page.save_revision())
        page = NoticePage.objects.get(pk=page.pk)
        self.assertTrue(page.live)  # 不中断
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)
        self.assertIn("PA25原标题", self.client.get(page.url).content.decode())
        run_publish_scheduled_at(due + MINUTE)
        page = NoticePage.objects.get(pk=page.pk)
        self.assertTrue(page.live)
        self.assertIn("PA25改版标题", self.client.get(page.url).content.decode())  # 修订生效


class ExpireBoundaryTests(BoundaryBase):
    """expire_at 侧边界（B06–B11/B13；PA-06..11/24/26）。"""

    def test_b06_live_with_future_expire_stays_visible(self):
        """PA-06（B13 同口径）：未来 expire_at 是 S2 的属性、不单设状态；
        到点前不因该字段离集。"""
        page = make_notice(self.container, slug="b06", title="B06在线页", publish=True)
        self.assertIsNotNone(page.expire_at)  # 首发即带未来有效期
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)
        self.assertTrue(page.in_current_default)
        self.assertEqual(self.client.get(page.url).status_code, 200)
        run_publish_scheduled_at(timezone.now())  # 未到点的常规周期运行
        page.refresh_from_db()
        self.assertTrue(page.live)
        self.assertIn("b06", set(current_default_pages().values_list("slug", flat=True)))

    def test_b07_exact_expire_boundary_strict_less(self):
        """PA-07：``expire_at__lt`` 严格比较——N == T 的运行不下线，
        首次 N > T 的运行执行 E7。"""
        due = timezone.now() + HOUR
        page = make_notice(self.container, slug="b07", publish=True)
        set_expire_at(page, due)
        run_publish_scheduled_at(due)  # N == T
        page.refresh_from_db()
        self.assertTrue(page.live)
        run_publish_scheduled_at(due + SECOND)  # 首次 N > T
        page.refresh_from_db()
        self.assertFalse(page.live)
        self.assertTrue(page.expired)

    def test_b08_expiry_exits_lists_zero_deletion(self):
        """PA-08：E7 后退出首页与默认列表；内容/修订/slug/URL 零删除。"""
        page = make_notice(self.container, slug="b08", title="B08到期页", publish=True)
        revisions_before = Revision.objects.filter(object_id=page.pk).count()
        set_expire_at(page, timezone.now() - HOUR)
        run_publish_scheduled_at(timezone.now())
        page = NoticePage.objects.get(pk=page.pk)
        self.assertEqual(page.lifecycle_state, LIFECYCLE_EXPIRED)
        self.assertFalse(page.in_current_default)
        # M5.2 §7.2 登记差异：expired 具名 URL 由 404 放行渲染（载体①）。
        self.assertEqual(self.client.get(page.url).status_code, 200)
        self.assertNotIn("B08到期页", self.client.get(self.section.url).content.decode())
        self.assertEqual(page.slug, "b08")  # slug/URL 零删除
        self.assertEqual(
            Revision.objects.filter(object_id=page.pk).count(), revisions_before
        )  # 修订史零删除
        self.assertTrue(NoticePage.objects.filter(pk=page.pk).exists())  # 行保留

    def test_b09_modify_expire_object_level_semantics(self):
        """PA-09：新值经 clean 未来性强制；仅存修订不发布不影响 live 现值
        （对象级生效），发布修订后旧时刻作废以新值为准。"""
        page = make_notice(self.container, slug="b09", publish=True)
        original = page.expire_at
        page.expire_at = timezone.now() - HOUR
        with self.assertRaises(ValidationError) as ctx:
            page.full_clean()  # 改过去被拒
        self.assertIn("expire_at", ctx.exception.error_dict)
        new_expire = future(days=7)  # 改晚/改早均合法（无最小间隔约束）
        page.expire_at = new_expire
        revision = page.save_revision()  # 仅存修订（clean 过，未发布）
        page.refresh_from_db()
        self.assertEqual(page.expire_at, original)  # 未发布修订不影响现值
        revision.publish()  # 发布修订
        page.refresh_from_db()
        self.assertEqual(page.expire_at, new_expire)  # 新值生效、旧时刻作废

    def test_b10_cancel_expire_policy_split(self):
        """PA-10：Article 可清空转常青；Notice 必填不可取消
        （常青三类强制空见既有 ForbiddenWindowTests）。"""
        article = make_article(self.container, slug="b10-a", publish=True)
        article.expire_at = future(days=7)
        article.full_clean()  # 有值合法
        article.expire_at = None
        article.full_clean()  # 取消＝清空转常青（退场回落 E8 手动下线）
        notice = make_notice(self.container, slug="b10-n")
        notice.expire_at = None
        with self.assertRaises(ValidationError) as ctx:
            notice.full_clean()  # CM-01：必填不可取消
        self.assertIn("expire_at", ctx.exception.error_dict)

    def test_b11_republish_enforces_new_window(self):
        """PA-11：E9 publish 原子置 expired=False；Notice 新未来有效期经
        clean 强制（过去值在 save_revision 闸口被拒）；重设期按新值生效。"""
        page = make_notice(self.container, slug="b11", publish=True)
        set_expire_at(page, timezone.now() - HOUR)
        run_publish_scheduled_at(timezone.now())
        page = NoticePage.objects.get(pk=page.pk)
        self.assertTrue(page.expired)
        page.expire_at = timezone.now() - HOUR
        with self.assertRaises(ValidationError):
            page.save_revision()  # clean 闸口：重发布须给新未来有效期
        page.expire_at = future(days=7)
        page.publish(page.save_revision())  # E9
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_LIVE)
        self.assertFalse(page.expired)  # 原子复位
        set_expire_at(page, timezone.now() - MINUTE)  # 重设期（2.3 口径）
        run_publish_scheduled_at(timezone.now())
        page.refresh_from_db()
        self.assertEqual(page.lifecycle_state, LIFECYCLE_EXPIRED)  # 按新值生效

    def test_pa24_expired_renders_archive_surface_registered(self):
        """PA-24（M5.2 起口径翻转）：V1 期守门「到期 404＋URL 位点零
        archive 留痕」由 M5.2 正式落地取代（§6.3 载体①/§6.1 归档视图）——
        expired 原 URL 放行渲染；默认列表仍不含；archive 位点由零改在册
        （section-archive，五板块归档视图）。"""
        page = make_notice(self.container, slug="pa24", title="PA24过期页", publish=True)
        set_expire_at(page, timezone.now() - HOUR)
        run_publish_scheduled_at(timezone.now())
        page.refresh_from_db()
        self.assertEqual(self.client.get(page.url).status_code, 200)  # 载体①放行
        self.assertNotIn("PA24过期页", self.client.get(self.section.url).content.decode())
        names = set()
        _collect_url_names(get_resolver(), names)
        self.assertEqual(
            sorted(n for n in names if "archive" in n), ["section-archive"]
        )  # M5.2 归档视图在册（唯一位点）

    def test_pa26_non_live_never_expires(self):
        """PA-26：draft/scheduled 页的 expire_at 永不触发转换（过期集自带
        live=True 过滤＋unpublish 短路；细粒度反例见 IllegalEdgeTests）。"""
        draft = make_notice(self.container, slug="pa26-d")
        scheduled = make_notice(
            self.container, slug="pa26-s", schedule_at=timezone.now() + 2 * HOUR
        )
        set_expire_at(draft, timezone.now() - HOUR)
        set_expire_at(scheduled, timezone.now() - HOUR)
        run_publish_scheduled_at(timezone.now() + HOUR)
        draft.refresh_from_db()
        scheduled.refresh_from_db()
        self.assertEqual(draft.lifecycle_state, LIFECYCLE_DRAFT)
        self.assertEqual(scheduled.lifecycle_state, LIFECYCLE_SCHEDULED)


class CommandBehaviorTests(BoundaryBase):
    """命令行为边界（B14/B15；PA-13/14/20/21/22/27）。"""

    def test_b14_rerun_same_moment_zero_change(self):
        """PA-13：同刻重跑第二次零状态变更（幂等三重保证：live=F 不入过期
        集、unpublish 短路、已发布修订 approved 已清）。"""
        page = make_notice(self.container, slug="b14-e", publish=True)
        set_expire_at(page, timezone.now() - HOUR)
        run_publish_scheduled_at(timezone.now())
        page = NoticePage.objects.get(pk=page.pk)
        self.assertFalse(page.live)
        self.assertTrue(page.expired)
        fingerprint = (
            page.live,
            page.expired,
            page.last_published_at,
            page.live_revision_id,
            Revision.objects.filter(object_id=page.pk).count(),
        )
        run_publish_scheduled_at(timezone.now())  # 同刻重跑（到期相）
        page = NoticePage.objects.get(pk=page.pk)
        self.assertEqual(
            (
                page.live,
                page.expired,
                page.last_published_at,
                page.live_revision_id,
                Revision.objects.filter(object_id=page.pk).count(),
            ),
            fingerprint,
        )
        due = timezone.now() + 10 * MINUTE  # 预约相
        scheduled = make_notice(self.container, slug="b14-s", schedule_at=due)
        run_publish_scheduled_at(due + 10 * MINUTE)
        scheduled = NoticePage.objects.get(pk=scheduled.pk)
        self.assertTrue(scheduled.live)
        self.assertEqual(
            Revision.objects.filter(
                object_id=scheduled.pk, approved_go_live_at__isnull=False
            ).count(),
            0,
        )
        state = (scheduled.live, scheduled.last_published_at, scheduled.live_revision_id)
        run_publish_scheduled_at(due + 10 * MINUTE)  # 同刻重跑（预约相）
        scheduled = NoticePage.objects.get(pk=scheduled.pk)
        self.assertEqual(
            (scheduled.live, scheduled.last_published_at, scheduled.live_revision_id), state
        )

    def test_b15_failure_interrupts_then_next_run_catches_up(self):
        """PA-14：单项失败中断本次运行但不回滚已处理项；下期工作集重推导
        自动补执行全部积压（无下限过滤）。"""
        now = timezone.now()
        page_ok = make_notice(self.container, slug="b15-ok", publish=True)
        page_fail = make_notice(self.container, slug="b15-fail", publish=True)
        page_late = make_notice(self.container, slug="b15-late", publish=True)
        # 过期集按 expire_at 升序处理：ok → fail（注入中断）→ late（未触及）
        set_expire_at(page_ok, now - 3 * HOUR)
        set_expire_at(page_fail, now - 2 * HOUR)
        set_expire_at(page_late, now - HOUR)
        original_unpublish = Page.unpublish

        def flaky_unpublish(self, *args, **kwargs):
            if self.pk == page_fail.pk:
                raise RuntimeError("PA-14 注入：到期处理中断")
            return original_unpublish(self, *args, **kwargs)

        with mock.patch.object(Page, "unpublish", flaky_unpublish):
            with self.assertRaises(RuntimeError):  # 命令无逐项 try/except，整体中断
                call_command("publish_scheduled", verbosity=0)
        page_ok = NoticePage.objects.get(pk=page_ok.pk)
        page_fail = NoticePage.objects.get(pk=page_fail.pk)
        page_late = NoticePage.objects.get(pk=page_late.pk)
        self.assertTrue(page_ok.expired)  # 已处理项保持已处理（save 已落库不回滚）
        self.assertFalse(page_ok.live)
        self.assertTrue(page_fail.live)  # 失败项原样留待下次
        self.assertFalse(page_fail.expired)
        self.assertTrue(page_late.live)  # 中断点之后的积压项未处理
        call_command("publish_scheduled", verbosity=0)  # 下一周期自动补执行
        for page in (page_ok, page_fail, page_late):
            page.refresh_from_db()
            self.assertTrue(page.expired)
            self.assertFalse(page.live)

    def test_pa20_strict_less_both_phases(self):
        """PA-20：两相均为严格 <（publish_scheduled.py 过滤位点）；"精确到点"
        的单次运行两相均不动作（细粒度半边见 PA-02/PA-07 各测试）。"""
        due = timezone.now() + 10 * MINUTE
        scheduled = make_notice(self.container, slug="pa20-s", schedule_at=due)
        expiring = make_notice(self.container, slug="pa20-e", publish=True)
        set_expire_at(expiring, due)
        run_publish_scheduled_at(due)  # N == T：预约不发布、到期不下线
        scheduled.refresh_from_db()
        expiring.refresh_from_db()
        self.assertEqual(scheduled.lifecycle_state, LIFECYCLE_SCHEDULED)
        self.assertTrue(expiring.live)
        run_publish_scheduled_at(due + SECOND)  # 首次 N > T：两相各自动作
        scheduled.refresh_from_db()
        expiring.refresh_from_db()
        self.assertTrue(scheduled.live)
        self.assertTrue(expiring.expired)

    def test_pa21_featured_and_site_settings_outside_workset(self):
        """PA-21：FeaturedItem/SiteSettings 非 DraftStateMixin，结构性不在
        命令工作集；展示窗口是请求时计算，无任务依赖。"""
        now = timezone.now()
        page = make_notice(self.container, slug="pa21", publish=True)
        featured = make_featured(page, start=now - 2 * HOUR, end=now - HOUR)  # 窗口已过
        site = Site.objects.get(is_default_site=True)
        settings_obj = SiteSettings.objects.create(
            site=site,
            feedback_email="pa21@test",
            alert_text="PA21提示",
            alert_start_at=now - 2 * HOUR,
            alert_end_at=now - HOUR,
        )
        self.assertFalse(issubclass(FeaturedItem, DraftStateMixin))
        self.assertFalse(issubclass(SiteSettings, DraftStateMixin))
        run_publish_scheduled_at(now + HOUR)
        featured = FeaturedItem.objects.get(pk=featured.pk)
        self.assertTrue(featured.enabled)  # 命令零触碰
        self.assertEqual(featured.start_at, now - 2 * HOUR)
        self.assertEqual(featured.end_at, now - HOUR)
        settings_obj.refresh_from_db()
        self.assertEqual(settings_obj.alert_text, "PA21提示")

    def test_pa21_display_window_request_time_semantics(self):
        """PA-21 后半：展示有效性随请求时刻翻转，不经任何任务（§5.2.2）。"""
        page = make_notice(self.container, slug="pa21-rt", publish=True)
        start, end = timezone.now() - HOUR, timezone.now() + HOUR
        item = make_featured(page, start=start, end=end)
        self.assertTrue(item.is_on_display(now=start + MINUTE))
        self.assertFalse(item.is_on_display(now=end + MINUTE))  # 零任务参与

    def test_pa22_within_hour_window_and_backlog_catch_up(self):
        """PA-22：到点→生效 ≤1 小时＋单次运行时长；工作集无下限，停机/失败
        错过的项恢复后自动补执行（production 每小时周期调用归 B6 落地）。"""
        now = timezone.now()
        fresh = make_notice(self.container, slug="pa22-f", schedule_at=now + 20 * MINUTE)
        stale = make_notice(self.container, slug="pa22-s", schedule_at=now + 10 * MINUTE)
        run_publish_scheduled_at(now + 59 * MINUTE)  # fresh 到点 39 分钟后（≤1h 窗口内）
        fresh.refresh_from_db()
        self.assertTrue(fresh.live)
        run_publish_scheduled_at(now + dt.timedelta(days=10))  # stale 积压 10 天仍补发
        stale.refresh_from_db()
        self.assertTrue(stale.live)

    def test_pa27_revision_date_expired_dead_code_unused(self):
        """PA-27：7.4.2 ``revision_date_expired`` 定义但无调用点——命令模块
        仅出现定义一处；项目生产代码零引用（过期判定以对象级列为准）。"""
        from wagtail.management.commands import publish_scheduled as command_module

        source = inspect.getsource(command_module)
        self.assertEqual(source.count("revision_date_expired"), 1)  # 仅 def 一处
        root = pathlib.Path(__file__).resolve().parent.parent
        for app_dir in ("src", "home", "departments", "guides", "notices", "resources", "search"):
            for path in (root / app_dir).rglob("*.py"):
                self.assertNotIn(
                    "revision_date_expired", path.read_text(encoding="utf-8"), msg=str(path)
                )


class FeaturedBoundaryTests(BoundaryBase):
    """推荐位交互边界（B16–B18；PA-15..18）。前台消费归 MB8——本组钉住
    is_on_display 谓词与其消费契约（§5.2.1：禁止仅按 enabled＋窗口渲染）。"""

    def _invisible_pages(self):
        """造 S0/S1/S3/S4 各一（窗口均覆盖当前时刻）。"""
        draft = make_notice(self.container, slug="fi-s0")
        scheduled = make_notice(self.container, slug="fi-s1", schedule_at=timezone.now() + HOUR)
        expiring = make_notice(self.container, slug="fi-s3", publish=True)
        set_expire_at(expiring, timezone.now() - HOUR)
        run_publish_scheduled_at(timezone.now())
        expiring.refresh_from_db()
        unpublished = make_notice(self.container, slug="fi-s4", publish=True)
        unpublished.unpublish()
        return draft, scheduled, expiring, unpublished

    def test_pa15_window_closed_interval(self):
        """PA-15：起止闭区间（含两端，§5.2.7——与生命周期侧严格 < 是不同
        对象的边界口径，不得混用）；窗外不展示。"""
        page = make_notice(self.container, slug="fi-b17", publish=True)
        start, end = timezone.now() - HOUR, timezone.now() + HOUR
        item = make_featured(page, start=start, end=end)
        self.assertTrue(item.is_on_display(now=start))  # N == start：当刻有效
        self.assertTrue(item.is_on_display(now=end))  # N == end：当刻有效
        self.assertFalse(item.is_on_display(now=start - SECOND))  # 窗外前
        self.assertFalse(item.is_on_display(now=end + SECOND))  # 窗外后

    def test_pa16_invisible_states_never_on_display(self):
        """PA-16：所指页 ∉ CURRENT_DEFAULT（S0/S1/S3/S4）即不展示——推荐位
        不是绕过预约的旁路，expired/offline 不残留默认前台。"""
        live = make_notice(self.container, slug="fi-s2", publish=True)
        for page in self._invisible_pages():
            with self.subTest(state=page.lifecycle_state):
                item = make_featured(page)
                self.assertFalse(item.is_on_display())
        self.assertTrue(make_featured(live).is_on_display())  # 对照组：仅 S2 成立

    def test_pa17_invalid_items_skipped_no_error(self):
        """PA-17：引用不可见内容的推荐项被逐项过滤跳过——不占位、不抛错
        （标题/摘要不进入有效集＝不泄漏；渲染级不泄漏归 MB8 模板消费）；
        全无效时有效集为空（IA §7.1"空缺时区块整体不渲染"的数据侧前提）。"""
        invalid_page = make_notice(self.container, slug="fi-d-inv")  # S0
        valid_page = make_notice(self.container, slug="fi-d-val", publish=True)
        make_featured(invalid_page)
        valid = make_featured(valid_page)
        displayed = [fi.pk for fi in FeaturedItem.objects.order_by("pk") if fi.is_on_display()]
        self.assertEqual(displayed, [valid.pk])  # 无效项跳过、不占位
        FeaturedItem.objects.filter(pk=valid.pk).delete()
        self.assertEqual(
            [fi for fi in FeaturedItem.objects.all() if fi.is_on_display()], []
        )  # 全无效 → 空集（区块整体不渲染的谓词侧依据）

    def test_pa18_slot_cap_is_display_layer_contract(self):
        """PA-18：数量固定是展示层规则（IA §7.2）——模型不落槽位/排序字段，
        管理侧可超额登记（超出部分展示侧不渲染＝MB8 按固定常量截断；V1
        默认建议 6 待项目负责人确认，站点级配置留痕、不写入模型字段）。"""
        field_names = {f.name for f in FeaturedItem._meta.concrete_fields}
        self.assertFalse({"slot", "position", "sort_order", "ordering"} & field_names)
        page = make_notice(self.container, slug="fi-b18", publish=True)
        for _ in range(8):  # 8 > 6：截断归 MB8 消费侧
            make_featured(page)
        self.assertEqual(FeaturedItem.objects.count(), 8)


class TimezoneInvariantTests(BoundaryBase):
    """PA-19（§4.2/§4.4④）：时间边界全 aware；TIME_ZONE 取值不影响 E3/E7
    判定与 CURRENT_DEFAULT 成员（业务时区仅作用于输入/显示两个钟面层）。"""

    def test_boundaries_are_timezone_aware(self):
        page = make_notice(self.container, slug="tz-aware", schedule_at=timezone.now() + HOUR)
        expiring = make_notice(self.container, slug="tz-aware-e", publish=True)
        featured = make_featured(expiring)
        page = NoticePage.objects.get(pk=page.pk)
        approved = Revision.objects.get(
            object_id=page.pk, approved_go_live_at__isnull=False
        ).approved_go_live_at
        for label, value in (
            ("go_live_at", page.go_live_at),
            ("expire_at", page.expire_at),
            ("approved_go_live_at", approved),
            ("start_at", featured.start_at),
            ("end_at", featured.end_at),
        ):
            with self.subTest(field=label):
                self.assertTrue(timezone.is_aware(value))  # 禁 naive datetime

    def test_time_zone_value_does_not_change_scheduling_outcomes(self):
        """§4.4④：同一绝对时刻在两种 TIME_ZONE 配置下 E3/E7 判定与
        CURRENT_DEFAULT 成员完全一致（绝对时刻等价；钟面层确已不同，
        证明覆盖非空）。"""
        results, offsets = {}, {}
        for tz_name in ("UTC", "Asia/Shanghai"):
            with override_settings(TIME_ZONE=tz_name):
                anchor = timezone.now()
                offsets[tz_name] = timezone.localtime(anchor).utcoffset()
                prefix = "tz-u" if tz_name == "UTC" else "tz-c"
                scheduled = make_notice(
                    self.container, slug=f"{prefix}-sch", schedule_at=anchor + 2 * HOUR
                )
                expiring = make_notice(self.container, slug=f"{prefix}-exp", publish=True)
                set_expire_at(expiring, anchor + HOUR)
                run_publish_scheduled_at(anchor + 3 * HOUR)
                scheduled = NoticePage.objects.get(pk=scheduled.pk)
                expiring = NoticePage.objects.get(pk=expiring.pk)
                results[tz_name] = (
                    scheduled.live,
                    scheduled.lifecycle_state,
                    scheduled.in_current_default,
                    expiring.expired,
                    expiring.lifecycle_state,
                    expiring.in_current_default,
                )
        self.assertNotEqual(offsets["UTC"], offsets["Asia/Shanghai"])  # 钟面层不同
        self.assertEqual(results["UTC"], results["Asia/Shanghai"])  # 判定层等价
        self.assertEqual(
            results["Asia/Shanghai"],
            (
                True,
                LIFECYCLE_LIVE,
                True,
                True,
                LIFECYCLE_EXPIRED,
                False,
            ),
        )


class MachineGuardTests(SimpleTestCase):
    """PA-23/30：机器形状与测试实现约束（无 DB）。"""

    def test_pa23_no_parallel_publication_state_fields(self):
        """PA-23：不建第二套 scheduled/expiry 状态字段——S0–S4 由内建列纯
        推导（mixin 零字段半边见 test_lifecycle_state.MachineShapeTests）。"""
        forbidden = {
            "scheduled_status",
            "expiry_status",
            "publish_state",
            "publication_state",
            "archive_status",
            "schedule_state",
        }
        for model in (NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage):
            with self.subTest(model=model.__name__):
                names = {f.name for f in model._meta.concrete_fields}
                self.assertFalse(names & forbidden)
                self.assertIn("expired", names)  # 到期仅消费 Wagtail 内建列

    def test_pa30_no_sleep_in_test_suite(self):
        """PA-30：调度测试禁 sleep——时间推进只经 mock timezone.now 或 DB
        直设时间后跑正式命令（本套件全量静态 guard）。"""
        pattern = re.compile(r"\bsleep\s*\(")
        offenders = [
            path.name
            for path in pathlib.Path(__file__).resolve().parent.glob("test_*.py")
            if pattern.search(path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(offenders, [])
