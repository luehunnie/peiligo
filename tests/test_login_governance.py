"""F-05 登录治理回归（SB §10-1 / SEC-01）。

断言面：密码最短 12 位（AUTH_PASSWORD_VALIDATORS 原生
MinimumLengthValidator，OPTIONS 冻结值直证）；django-axes 限速＝10 次失败
→ 锁 15 分钟（第 10 次失败即 HTTP 429 锁定响应，锁定期内正确密码同样
拒绝，cooloff 过后自动解锁）、成功登录清零计数（AXES_RESET_ON_SUCCESS）；
会话 24h
（SESSION_COOKIE_AGE）；改密后旧会话失效（Django 原生 session hash 机制，
零新增代码的行为级回归）。axes 兼容性事实：DB 存储处理器（无 Redis）、
AxesStandaloneBackend 置首而 ModelBackend 仍为唯一凭据校验者（无第二套
认证系统）；Wagtail admin 登录视图继承 Django LoginView，同链路覆盖。
"""

from datetime import timedelta

from axes.models import AccessAttempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.utils import timezone

User = get_user_model()

LOGIN_URL = "/admin/login/"
PASSWORD = "t44-pass-12345"  # 与 tests/permission_helpers 同值口径（≥12 位）
# axes 8.x 锁定响应＝HTTP 429 Too Many Requests（AxesMiddleware 缺省）。
LOCKOUT_STATUS = 429


def _post_login(client, username, password):
    return client.post(LOGIN_URL, {"username": username, "password": password})


class PasswordMinLengthTests(TestCase):
    """密码最短 12 位：设置冻结值直证＋validator 边界行为。"""

    def test_settings_freeze_min_length_12(self):
        minimum = [
            validator
            for validator in settings.AUTH_PASSWORD_VALIDATORS
            if validator["NAME"].endswith("MinimumLengthValidator")
        ]
        self.assertEqual(len(minimum), 1)
        self.assertEqual(minimum[0]["OPTIONS"]["min_length"], 12)

    def test_validate_password_boundary(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_password("a" * 11)
        self.assertIn("12", " ".join(ctx.exception.messages))
        validate_password("a" * 12)  # 不抛＝通过


@override_settings(AXES_ENABLED=True)
class AxesLockoutTests(TestCase):
    """django-axes：10 次失败锁 15 分钟；成功登录清零（SB §10-1 冻结值）。

    类级重开 AXES_ENABLED（tests/conftest.py 会话级默认关停——Client.login
    兼容口径），本类全部经视图 POST 驱动完整 axes 链路。
    """

    def setUp(self):
        self.user = User.objects.create_user("axes-user", password=PASSWORD)
        self.client = Client()

    def test_settings_freeze_10_15_reset(self):
        self.assertEqual(settings.AXES_FAILURE_LIMIT, 10)
        self.assertEqual(settings.AXES_COOLOFF_TIME, timedelta(minutes=15))
        self.assertTrue(settings.AXES_RESET_ON_SUCCESS)
        # R 审查 M1：锁定键＝SB §2.3 建议 username＋ip 组合（非 axes 缺省
        # 的仅 IP——校园 NAT 共享出口下仅 IP 会误锁全站点）。
        self.assertEqual(settings.AXES_LOCKOUT_PARAMETERS, [["username", "ip_address"]])

    def test_same_ip_cross_username_failures_do_not_lock_site(self):
        """组合键行为级：同 IP 多账号分散失败不锁全站点（仅 IP 键将误锁）。"""
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        for i in range(10):
            user_model.objects.create_user(f"cross-user-{i}", password=PASSWORD)
            response = _post_login(self.client, f"cross-user-{i}", "wrong-password-1")
            self.assertEqual(response.status_code, 200, f"账号 {i} 每键独立计数")
        fresh = user_model.objects.create_user("cross-user-fresh", password=PASSWORD)
        response = _post_login(self.client, fresh.username, PASSWORD)
        self.assertEqual(response.status_code, 302, "同 IP 他账号失败不牵连新账号登录")

    def test_axes_apps_and_backends_wiring(self):
        """接线事实：axes 入 INSTALLED_APPS＋中间件；ModelBackend 仍在
        AUTHENTICATION_BACKENDS（axes 非第二套认证系统，仅前置闸门）。"""
        self.assertIn("axes", settings.INSTALLED_APPS)
        self.assertIn("axes.middleware.AxesMiddleware", settings.MIDDLEWARE)
        self.assertEqual(settings.AUTHENTICATION_BACKENDS[0], "axes.backends.AxesStandaloneBackend")
        self.assertIn("django.contrib.auth.backends.ModelBackend", settings.AUTHENTICATION_BACKENDS)

    def test_nine_failures_then_correct_login_succeeds(self):
        for _ in range(9):
            response = _post_login(self.client, "axes-user", "wrong-password-1")
            self.assertEqual(response.status_code, 200)
        response = _post_login(self.client, "axes-user", PASSWORD)
        self.assertEqual(response.status_code, 302, "9 次失败未达上限，正确密码可登录")

    def test_tenth_failure_locks_and_correct_password_rejected_during_lockout(self):
        for _ in range(9):
            _post_login(self.client, "axes-user", "wrong-password-1")
        response = _post_login(self.client, "axes-user", "wrong-password-1")
        self.assertEqual(response.status_code, LOCKOUT_STATUS, "第 10 次失败即锁定")
        response = _post_login(self.client, "axes-user", PASSWORD)
        self.assertEqual(response.status_code, LOCKOUT_STATUS, "锁定期内正确密码同样拒绝")
        # 锁定后的尝试仍计数（AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT
        # 缺省开——锁内失败会顺延锁定窗口，防爆破方试探）。
        self.assertGreaterEqual(
            AccessAttempt.objects.get(username="axes-user").failures_since_start, 10
        )

    def test_lock_expires_after_fifteen_minutes(self):
        for _ in range(10):
            _post_login(self.client, "axes-user", "wrong-password-1")
        attempt = AccessAttempt.objects.get(username="axes-user")
        attempt.attempt_time = timezone.now() - timedelta(minutes=16)
        attempt.save()
        response = _post_login(self.client, "axes-user", PASSWORD)
        self.assertEqual(response.status_code, 302, "cooloff（15 分钟）过后自动解锁")

    def test_success_resets_failure_counter(self):
        """成功登录清零：两轮 6 次失败夹一次成功——累计 12 次不触发锁定。"""
        for _ in range(6):
            _post_login(self.client, "axes-user", "wrong-password-1")
        response = _post_login(self.client, "axes-user", PASSWORD)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AccessAttempt.objects.count(), 0, "成功登录即清零失败计数")
        for i in range(6):
            response = _post_login(self.client, "axes-user", "wrong-password-2")
            self.assertEqual(response.status_code, 200, f"清零后第 {i + 1} 次失败不应锁定")


class SessionGovernanceTests(TestCase):
    """会话 24h＋改密后旧会话失效（Django 原生 session hash 机制）。"""

    def setUp(self):
        from django.contrib.auth.models import Permission

        self.user = User.objects.create_user("sess-user", password=PASSWORD)
        # 授予后台访问位，使「GET /admin/ 200」可作会话有效性探针
        # （裸用户即使登录成功也会被重定向，探针失真）。
        self.user.is_staff = True
        self.user.save()
        self.user.user_permissions.add(
            Permission.objects.get(codename="access_admin", content_type__app_label="wagtailadmin")
        )

    def test_settings_freeze_session_age_24h(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 60 * 60 * 24)

    def test_password_change_invalidates_other_sessions(self):
        def admin_reachable(client):
            return client.get("/admin/").status_code == 200

        old_session = Client()
        self.assertTrue(old_session.login(username="sess-user", password=PASSWORD))
        self.assertTrue(admin_reachable(old_session))

        # 改密不经旧会话执行（等价"另一处"改密动作；Wagtail 账户页改密与
        # ORM set_password 最终都落 password 字段变更，session hash 随之失配）。
        self.user.set_password("t44-new-pass-67890")
        self.user.save()

        self.assertFalse(admin_reachable(old_session), "改密后旧会话必须失效")
        fresh = Client()
        self.assertTrue(fresh.login(username="sess-user", password="t44-new-pass-67890"))
