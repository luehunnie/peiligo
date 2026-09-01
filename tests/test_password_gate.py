"""F-05R（SB §2.4，断言锚点 SB-04/SEC-16）：强制改密闭环行为测试。

真实后台动线逐项核对冻结机制：
- ① PasswordState.password_last_set 属性：后台设置/重置 → 置空；
- ③ 服务端路由级拦截：已登录且未设定 → 任意后台路由 302 到改密页；
- ④ 首登改密＝同一机制（后台新建账号首登录即被拦截）；
- 改密成功 → 时刻落值、闸门解除、其余会话失效（SB 冻结规则）；
- 误伤面为零：未触碰密码的编辑、ORM/CLI 播种路径均不触发闸门；
- 自救面：被拦截者仍可登出；匿名不可达改密页；break-glass 命令留痕。

动线备注：wagtail UserForm 的 email/first_name/last_name 必填，且
groups 缺省＝清空组（会连带失去后台准入）——编辑 POST 一律带原组。
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse

from peiligo.passwordgate.models import PasswordState

from .permission_helpers import PASSWORD, build_permission_world, login_client

User = get_user_model()

RESET_PASSWORD = "t49-reset-pass-2468"  # 总管理员重置所用的临时口令（≥12 位）
FINAL_PASSWORD = "t49-final-pass-1357"  # 用户自行设定的新口令

USER_ADD_DATA = {
    "username": "t49-gated",
    "email": "gated@t49.example.com",
    "first_name": "强制",
    "last_name": "改密",
}


def gate_state(user_pk):
    return PasswordState.objects.filter(user_id=user_pk).first()


class AdminResetGateTests(TestCase):
    """②后台重置 → ③路由级拦截 → 改密释放的全动线。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        cls.admin = cls.world["admin"]

    def _admin_reset(self, user):
        client = login_client(self.admin)
        return client.post(
            reverse("wagtailusers_users:edit", args=[user.pk]),
            {
                "username": user.username,
                "email": "t49-reset@peiligo.example.com",
                "first_name": "测试",
                "last_name": "用户",
                "is_active": "on",
                "groups": [self.world["group_a"].pk],
                "password1": RESET_PASSWORD,
                "password2": RESET_PASSWORD,
            },
        )

    def test_admin_reset_forces_change_then_release(self):
        user = self.world["user_a"]
        self.assertEqual(self._admin_reset(user).status_code, 302)

        state = gate_state(user.pk)
        self.assertIsNotNone(state, "①密码设定时刻属性落行")
        self.assertIsNone(state.password_last_set, "②重置后时刻置空")

        victim = Client()
        self.assertTrue(victim.login(username=user.username, password=RESET_PASSWORD))
        resp = victim.get(reverse("wagtailadmin_home"))
        self.assertEqual(resp.status_code, 302, "③已登录未设定 → 拦截")
        self.assertEqual(resp["Location"], reverse("passwordgate_change"))

        self.assertEqual(victim.get(reverse("passwordgate_change")).status_code, 200)
        resp = victim.post(
            reverse("passwordgate_change"),
            {
                "old_password": RESET_PASSWORD,
                "new_password1": FINAL_PASSWORD,
                "new_password2": FINAL_PASSWORD,
            },
        )
        self.assertEqual(resp.status_code, 302, "改密成功 → 后台首页")
        state.refresh_from_db()
        self.assertIsNotNone(state.password_last_set, "改密完成 → 时刻落值")
        self.assertEqual(victim.get(reverse("wagtailadmin_home")).status_code, 200, "闸门解除")

    def test_wrong_old_password_keeps_gate(self):
        user = self.world["user_a"]
        self._admin_reset(user)
        victim = Client()
        self.assertTrue(victim.login(username=user.username, password=RESET_PASSWORD))
        resp = victim.post(
            reverse("passwordgate_change"),
            {
                "old_password": "t49-wrong-old-0000",
                "new_password1": FINAL_PASSWORD,
                "new_password2": FINAL_PASSWORD,
            },
        )
        self.assertEqual(resp.status_code, 200, "旧密码错误 → 表单驳回")
        self.assertIsNone(gate_state(user.pk).password_last_set, "闸门保持")
        self.assertEqual(victim.get(reverse("wagtailadmin_home")).status_code, 302)

    def test_stale_session_dies_on_reset(self):
        """SB 冻结规则：重置即失效他方会话（含改密前的旧会话）。"""
        user = self.world["user_a"]
        stale = Client()
        self.assertTrue(stale.login(username=user.username, password=PASSWORD))
        self.assertEqual(self._admin_reset(user).status_code, 302)
        resp = stale.get(reverse("wagtailadmin_home"))
        self.assertEqual(resp.status_code, 302, "旧会话已失效")
        self.assertNotIn("password-change", resp["Location"], "失效会话不再享有改密页")
        self.assertTrue(resp["Location"].startswith("/admin/login/"))


class FirstLoginGateTests(TestCase):
    """④后台新建账号（必填密码）→ 首登录即强制改密＝同一机制。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        cls.admin = cls.world["admin"]

    def test_admin_created_account_gated_on_first_login(self):
        client = login_client(self.admin)
        resp = client.post(
            reverse("wagtailusers_users:add"),
            {
                **USER_ADD_DATA,
                "groups": [self.world["group_a"].pk],
                "password1": RESET_PASSWORD,
                "password2": RESET_PASSWORD,
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="t49-gated")
        self.assertIsNone(gate_state(user.pk).password_last_set)

        victim = Client()
        self.assertTrue(victim.login(username=user.username, password=RESET_PASSWORD))
        resp = victim.get(reverse("wagtailadmin_home"))
        self.assertEqual(resp.status_code, 302, "首登录即被拦截")
        self.assertEqual(resp["Location"], reverse("passwordgate_change"))

        resp = victim.post(
            reverse("passwordgate_change"),
            {
                "old_password": RESET_PASSWORD,
                "new_password1": FINAL_PASSWORD,
                "new_password2": FINAL_PASSWORD,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(victim.get(reverse("wagtailadmin_home")).status_code, 200)


class NoFalsePositiveTests(TestCase):
    """闸门只认「后台设置/重置密码」动线，其余路径零误伤。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        cls.admin = cls.world["admin"]

    def test_edit_without_password_does_not_gate(self):
        user = self.world["user_a"]
        client = login_client(self.admin)
        resp = client.post(
            reverse("wagtailusers_users:edit", args=[user.pk]),
            {
                "username": user.username,
                "email": "renamed@t49.example.com",
                "first_name": "改名",
                "last_name": "用户",
                "is_active": "on",
                "groups": [self.world["group_a"].pk],
                "password1": "",
                "password2": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(gate_state(user.pk), "未触碰密码 → 不落状态行")
        self.assertEqual(
            login_client(user).get(reverse("wagtailadmin_home")).status_code,
            200,
            "普通编辑不触发闸门",
        )

    def test_orm_seeded_user_not_gated(self):
        user = User.objects.create_user("t49-orm", password=PASSWORD)
        user.groups.add(self.world["group_a"])  # ORM 播种照常入组（组带后台准入）
        self.assertIsNone(gate_state(user.pk), "ORM/CLI 播种路径不触发闸门")
        self.assertEqual(login_client(user).get(reverse("wagtailadmin_home")).status_code, 200)


class GateBoundaryTests(TestCase):
    """闸门边界：匿名、登出自救、break-glass 恢复路径。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        cls.admin = cls.world["admin"]
        client = login_client(cls.admin)
        client.post(
            reverse("wagtailusers_users:add"),
            {
                **USER_ADD_DATA,
                "groups": [cls.world["group_a"].pk],
                "password1": RESET_PASSWORD,
                "password2": RESET_PASSWORD,
            },
        )
        cls.gated = User.objects.get(username="t49-gated")

    def test_anonymous_cannot_reach_change_page(self):
        resp = Client().get(reverse("passwordgate_change"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/admin/login/"), "匿名 → 登录页")

    def test_flagged_user_can_still_logout(self):
        victim = Client()
        self.assertTrue(victim.login(username=self.gated.username, password=RESET_PASSWORD))
        resp = victim.post("/admin/logout/")
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("password-change", resp["Location"], "登出端点不被闸门拦截")

    def test_break_glass_command_releases_gate(self):
        victim = Client()
        self.assertTrue(victim.login(username=self.gated.username, password=RESET_PASSWORD))
        self.assertEqual(victim.get(reverse("wagtailadmin_home")).status_code, 302)

        buf = StringIO()
        call_command("clear_password_must_change", "--username", "t49-gated", stdout=buf)
        self.assertIn("t49-gated", buf.getvalue())
        self.assertIsNotNone(gate_state(self.gated.pk).password_last_set, "命令落时刻留痕")
        self.assertEqual(victim.get(reverse("wagtailadmin_home")).status_code, 200)

        # 命令对不存在账号显式报错，不静默
        with self.assertRaises(CommandError):
            call_command("clear_password_must_change", "--username", "t49-nonexistent")
