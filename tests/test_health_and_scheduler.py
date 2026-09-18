"""F-09：容器健康探针（/healthz/ /readyz/）与正式调度器（publish_scheduler）。

探针口径：最小 JSON 应答，失败态不携带任何环境细节（DB URL/路径/
栈回溯）；调度器口径：--once 单周期发布到期页，单次失败不抛出
（周期进程不因一次故障终止，容器 restart 策略另护进程级存活）。
"""

import datetime as dt
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .helpers import build_sections, make_container, make_department, make_notice

MINUTE = dt.timedelta(minutes=1)


class HealthEndpointTests(TestCase):
    def test_healthz_liveness_minimal_body(self):
        resp = self.client.get("/healthz/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_readyz_ok_when_db_available(self):
        resp = self.client.get("/readyz/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_readyz_503_without_leaking_details_when_db_down(self):
        with mock.patch("home.views.connection.cursor", side_effect=Exception("boom-secret")):
            resp = self.client.get("/readyz/")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json(), {"status": "unavailable"})
        self.assertNotIn(b"boom-secret", resp.content, "探针失败态不得泄露内部细节")


class SchedulerLoopTests(TestCase):
    """publish_scheduler --once：到期页发布＋失败吞入不终止。"""

    @classmethod
    def setUpTestData(cls):
        cls.section = build_sections()["chronicle"]
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.section, cls.department)

    def test_once_cycle_publishes_due_page_and_exits(self):
        due = timezone.now() + 5 * MINUTE
        page = make_notice(
            self.container,
            slug="f09-sched",
            title="F09到点页",
            schedule_at=due,
        )
        self.assertFalse(page.live, "预约页到点前不可见")

        buf = StringIO()
        with mock.patch("django.utils.timezone.now", return_value=due + MINUTE):
            call_command("publish_scheduler", "--once", stdout=buf)
        page.refresh_from_db()
        self.assertTrue(page.live, "调度器单周期发布到期页")
        self.assertIn("published=1", buf.getvalue(), "运行结果可观测")

    def test_cycle_failure_is_swallowed_not_raised(self):
        with mock.patch(
            "peiligo.applog.management.commands.publish_scheduler.call_command",
            side_effect=Exception("db-gone"),
        ):
            # 不抛出＝长驻循环不会因单次故障退出（下一周期重试）
            call_command("publish_scheduler", "--once", stderr=StringIO())

    def test_default_interval_meets_visibility_contract(self):
        """维护态缺省节拍 ≤30s（ADR-0008 Gate 5 验收条件）：预约发布
        ≤30s 可见契约以 `SCHED_INTERVAL_SECONDS ≤ 30` 承接——缺省回退值
        与 compose / deploy/.env.example 三处同源，本测试钉住命令侧不回退。"""
        import os

        from peiligo.applog.management.commands.publish_scheduler import Command

        env = os.environ.pop("SCHED_INTERVAL_SECONDS", None)
        try:
            parser = Command().create_parser("manage.py", "publish_scheduler")
            self.assertLessEqual(parser.get_default("interval"), 30)
        finally:
            if env is not None:
                os.environ["SCHED_INTERVAL_SECONDS"] = env
