"""F-07 结构化日志基础回归（SB §6.2 脱敏落地）。

断言面：JsonFormatter 稳定字段与敏感键清洗；LOGGING 接线事实（JSON
formatter、零文件 handler、logger 层级 ≥INFO＝SB §6.2 #4）；auth 信号
事件（login/login_failed/logout/axes locked_out）；Wagtail 内容事件
（published/unpublished，身份仅 username——SB §6.2 #3）；
run_publish_scheduled 包装命令的运行结果事件。
"""

import json
import logging
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from wagtail.models import Revision

from peiligo.logging_utils import SENSITIVE_KEYS, JsonFormatter, scrub_extra
from tests.test_ia_frontend import FrontendIATestCase

User = get_user_model()
PASSWORD = "t44-pass-12345"
EVENTS_LOGGER = "peiligo.events"


def _records_by_event(cm, event):
    """从 assertLogs 捕获中取指定事件码的 LogRecord。"""
    return [record for record in cm.records if getattr(record, "event", None) == event]


class JsonFormatterTests(TestCase):
    """格式化器：稳定字段＋脱敏＋异常字段。"""

    def _format(self, msg, level=logging.INFO, extra=None, exc_info=None):
        record = logging.LogRecord(
            name="peiligo.events",
            level=level,
            pathname=__file__,
            lineno=1,
            msg=msg,
            args=(),
            exc_info=exc_info,
        )
        for key, value in (extra or {}).items():
            setattr(record, key, value)
        return json.loads(JsonFormatter().format(record))

    def test_stable_fields(self):
        payload = self._format("你好日志")
        self.assertEqual(payload["event"], "app.log")
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "peiligo.events")
        self.assertEqual(payload["msg"], "你好日志")
        self.assertIn("T", payload["ts"])  # ISO-8601 UTC

    def test_error_level_defaults_to_app_error_event(self):
        payload = self._format("出错了", level=logging.ERROR)
        self.assertEqual(payload["event"], "app.error")

    def test_extra_fields_flattened_with_stable_event(self):
        payload = self._format("页面发布", extra={"event": "content.published", "page_id": 7})
        self.assertEqual(payload["event"], "content.published")
        self.assertEqual(payload["page_id"], 7)

    def test_sensitive_keys_scrubbed(self):
        payload = self._format(
            "x",
            extra={
                "password": "leak-me",
                "Secret": "leak-me",
                "token": "leak-me",
                "username": "op-a",
            },
        )
        self.assertNotIn("password", payload)
        self.assertNotIn("Secret", payload)
        self.assertNotIn("token", payload)
        self.assertEqual(payload["username"], "op-a")

    def test_scrub_extra_and_sensitive_keys_facts(self):
        self.assertIn("password", SENSITIVE_KEYS)
        self.assertIn("environ", SENSITIVE_KEYS)
        cleaned = scrub_extra({"password": "x", "session": "y", "ip": "1.2.3.4"})
        self.assertEqual(cleaned, {"ip": "1.2.3.4"})

    def test_exception_payload(self):
        try:
            raise ValueError("boom")
        except ValueError:
            payload = self._format("失败", level=logging.ERROR, exc_info=True)
        self.assertEqual(payload["exc"]["type"], "ValueError")
        self.assertEqual(payload["exc"]["value"], "boom")
        self.assertIn("Traceback", payload["exc"]["stack"])


class LoggingWiringTests(TestCase):
    """LOGGING 接线事实：JSON formatter／零文件 handler／层级 ≥INFO。"""

    def test_wiring_facts(self):
        config = settings.LOGGING
        self.assertEqual(config["version"], 1)
        self.assertFalse(config["disable_existing_loggers"])
        self.assertEqual(config["formatters"]["json"]["()"], "peiligo.logging_utils.JsonFormatter")
        for handler in config["handlers"].values():
            self.assertTrue(
                handler["class"].endswith("StreamHandler"),
                "F-07 口径：零文件 handler，日志入 stdout 由运行环境轮转",
            )
        levels = [cfg["level"] for cfg in config["loggers"].values()]
        levels.append(config["root"]["level"])
        for level in levels:
            self.assertGreaterEqual(logging.getLevelName(level), logging.INFO)

    def test_applog_installed(self):
        self.assertIn("peiligo.applog", settings.INSTALLED_APPS)


class AuthEventTests(TestCase):
    """auth/axes 信号 → 结构化事件（行为级，经 Client 完整链路）。"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("auth-log-user", password=PASSWORD)

    def test_login_failed_event(self):
        with self.assertLogs(EVENTS_LOGGER, "WARNING") as cm:
            self.client.post("/admin/login/", {"username": "auth-log-user", "password": "wrong"})
        records = _records_by_event(cm, "auth.login_failed")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].username, "auth-log-user")
        self.assertEqual(records[0].ip, "127.0.0.1")

    def test_login_and_logout_events(self):
        with self.assertLogs(EVENTS_LOGGER, "INFO") as cm:
            self.assertTrue(self.client.login(username="auth-log-user", password=PASSWORD))
            self.client.logout()
        events = [getattr(record, "event", None) for record in cm.records]
        self.assertIn("auth.login", events)
        self.assertIn("auth.logout", events)

    @override_settings(AXES_ENABLED=True)
    def test_axes_locked_out_event(self):
        with self.assertLogs(EVENTS_LOGGER, "WARNING") as cm:
            for _ in range(11):
                self.client.post(
                    "/admin/login/", {"username": "auth-log-user", "password": "wrong"}
                )
        records = _records_by_event(cm, "auth.locked_out")
        self.assertGreaterEqual(len(records), 1, "锁定时（含锁内续试）须发锁定事件")
        self.assertTrue(all(record.username == "auth-log-user" for record in records))


class ContentEventTests(FrontendIATestCase):
    """Wagtail 页面信号 → 结构化事件（元数据面，身份仅 username）。"""

    def test_publish_and_unpublish_events(self):
        from tests.helpers import make_article

        with self.assertLogs(EVENTS_LOGGER, "INFO") as cm:
            page = make_article(self.container, slug="log-article", publish=True)
        records = _records_by_event(cm, "content.published")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].page_id, page.pk)
        self.assertEqual(records[0].slug, "log-article")
        self.assertEqual(records[0].username, "-")  # ORM 动线无操作人＝占位，不臆造

        with self.assertLogs(EVENTS_LOGGER, "INFO") as cm:
            page.unpublish()
        self.assertEqual(len(_records_by_event(cm, "content.unpublished")), 1)


class PublishScheduledLogTests(FrontendIATestCase):
    """run_publish_scheduled 包装命令：运行结果结构化事件＋真实发布。"""

    def test_run_publishes_due_revision_and_logs_result(self):
        from datetime import timedelta

        from django.utils import timezone

        from tests.helpers import make_article, past

        page = make_article(self.container, slug="sched-log")
        page.go_live_at = timezone.now() + timedelta(days=1)
        revision = page.save_revision()
        revision.publish()  # 预约发布：live 仍 False，approved_go_live_at 在未来
        page.refresh_from_db()
        self.assertFalse(page.live)

        # 回拨为已过期 → 命令运行即真实发布。修订行与 content JSON 的
        # go_live_at 须同步（Revision.publish 按内容态 go_live_at 重新推导
        # 调度，仅改行字段会被再度预约而非上线）。
        due_at = past(1)
        revision.content["go_live_at"] = timezone.localtime(due_at).isoformat()
        revision.approved_go_live_at = due_at
        revision.save()

        with self.assertLogs(EVENTS_LOGGER, "INFO") as cm:
            call_command("run_publish_scheduled", stdout=StringIO())

        records = _records_by_event(cm, "publish_scheduled.run")
        self.assertEqual(len(records), 1)
        self.assertGreaterEqual(records[0].published, 1)
        self.assertGreaterEqual(records[0].due_before, 1)

        page.refresh_from_db()
        self.assertTrue(page.live)
        self.assertEqual(
            Revision.page_revisions.filter(approved_go_live_at__lte=past(0)).count(), 0
        )
