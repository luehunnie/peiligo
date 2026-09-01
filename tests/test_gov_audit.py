"""F-08B（R-05 方案 B）：用户/组治理操作 DB 级审计行为测试。

真实后台动线 → wagtail ModelLogEntry 落行 → actor/target/明细逐项核对：
- 用户/组 CRUD 主行（官方 wagtail.create/edit/delete，actor＝请求操作者）；
- 组员变动（用户编辑表单勾组）与组权限变更（组编辑表单勾权限）明细行；
- 对象删除后审计行保留（§8 不可随对象消失）；
- 非请求上下文（ORM 播种）照记但 actor 置空＋actor_type=non_request
  （§9 不伪造 system）；
- 治理总览页 /admin/gov-audit/ 可达性＋权限门＋筛选。
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from wagtail.models import ModelLogEntry

from .permission_helpers import PASSWORD, build_permission_world, login_client

User = get_user_model()

# 组编辑页五个权限面板 formset（页面/站点设置/文档/图片/集合管理）的管理
# 表单，前缀＝wagtail 面板 formset 的 default_prefix（<model_name>_permissions
# ＋站点设置面板的项目级前缀）。
GROUP_FORMSET = {
    f"{prefix}-{field}": value
    for prefix in (
        "page_permissions",
        "home_sitesettings_site_permissions",
        "document_permissions",
        "image_permissions",
        "collection_permissions",
    )
    for field, value in (
        ("TOTAL_FORMS", "0"),
        ("INITIAL_FORMS", "0"),
        ("MIN_NUM_FORMS", "0"),
        ("MAX_NUM_FORMS", "1000"),
    )
}


def user_entries(user_pk):
    return ModelLogEntry.objects.filter(
        content_type__app_label="auth", content_type__model="user", object_id=str(user_pk)
    )


def group_entries(group_pk):
    return ModelLogEntry.objects.filter(
        content_type__app_label="auth", content_type__model="group", object_id=str(group_pk)
    )


class UserCrudAuditTests(TestCase):
    """真实后台动线：建/改/删 用户 → 审计行 actor/target 逐项核对。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        cls.admin = cls.world["admin"]

    def test_user_create_edit_delete_full_audit_trail(self):
        w = self.world
        client = login_client(self.admin)

        resp = client.post(
            reverse("wagtailusers_users:add"),
            {
                "username": "t48-audit-u",
                "email": "audit@t48.example.com",
                "first_name": "审计",
                "last_name": "岗位",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        user = User.objects.get(username="t48-audit-u")
        self.assertEqual(resp.status_code, 302)
        create_row = user_entries(user.pk).filter(action="wagtail.create").get()
        self.assertEqual(create_row.user_id, self.admin.pk, "actor＝执行创建的管理员")
        self.assertEqual(create_row.label, "t48-audit-u")

        # 编辑（含组勾选）→ wagtail.edit 主行 ＋ 组员变动明细行
        resp = client.post(
            reverse("wagtailusers_users:edit", args=[user.pk]),
            {
                "username": "t48-audit-u",
                "email": "audit@t48.example.com",
                "first_name": "审计",
                "last_name": "岗位",
                "is_active": "on",
                "groups": [w["group_a"].pk],
                "password1": "",
                "password2": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            user_entries(user.pk).filter(action="wagtail.edit", user_id=self.admin.pk).exists()
        )
        member_row = user_entries(user.pk).filter(action="peiligo.gov.membership_changed").get()
        self.assertEqual(member_row.user_id, self.admin.pk, "明细行 actor 同为请求操作者")
        self.assertEqual(member_row.data["groups"], [w["group_a"].name])
        self.assertEqual(member_row.data["actor_type"], "request")

        # 删除 → wagtail.delete 行落库，且此前审计行全部保留（§8）
        resp = client.post(reverse("wagtailusers_users:delete", args=[user.pk]), {})
        self.assertEqual(resp.status_code, 302)
        before = user_entries(user.pk).count()
        self.assertGreaterEqual(before, 3, "删除后 create/edit/membership 行不消失")
        delete_row = user_entries(user.pk).filter(action="wagtail.delete").get()
        self.assertEqual(delete_row.user_id, self.admin.pk)
        self.assertFalse(User.objects.filter(pk=user.pk).exists(), "对象确已删除")

    def test_official_history_view_renders_for_user(self):
        w = self.world
        client = login_client(self.admin)
        resp = client.get(reverse("wagtailusers_users:history", args=[w["user_a"].pk]))
        self.assertEqual(resp.status_code, 200, "官方 History 视图经注册即刻可用")

    def test_gov_audit_view_gate_and_filter(self):
        w = self.world
        resp = login_client(self.admin).get(reverse("govaudit"))
        self.assertEqual(resp.status_code, 200, "R1 行权者可读治理总览")

        # 先以 admin 身份真实建一个用户，再按 操作者＋对象类型 筛选
        client = login_client(self.admin)
        client.post(
            reverse("wagtailusers_users:add"),
            {
                "username": "t48-filter-u",
                "email": "filter@t48.example.com",
                "first_name": "筛选",
                "last_name": "样例",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        resp = client.get(reverse("govaudit"), {"target": "user", "actor": self.admin.pk})
        self.assertEqual(resp.status_code, 200)
        rows = resp.context["object_list"]
        self.assertTrue(rows, "筛选应有命中（admin 动线已产生行）")
        self.assertTrue(all(r.content_type.model == "user" for r in rows))
        self.assertTrue(all(r.user_id == self.admin.pk for r in rows))

        resp = login_client(w["user_a"]).get(reverse("govaudit"))
        # 无 R1 行权面 → 视图抛 PermissionDenied，被 require_admin_access
        # 捕获后重定向后台首页（wagtail permission_denied 口径），不泄露行数据
        self.assertEqual(resp.status_code, 302, "部门内容账号被拒治理总览")
        self.assertNotIn("gov-audit", resp["Location"])


class GroupCrudAuditTests(TestCase):
    """真实后台动线：建/改/删 组＋权限逐项变更。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        cls.admin = cls.world["admin"]
        cls.add_doc_perm = Permission.objects.get(
            codename="add_department", content_type__app_label="departments"
        )  # 组编辑表单可选面＝项目 register_permissions 注册的词表权限

    def _group_post(self, name, permissions=()):
        data = {"name": name, "permissions": list(permissions), **GROUP_FORMSET}
        return data

    def test_group_create_permission_change_delete(self):
        client = login_client(self.admin)

        resp = client.post(reverse("wagtailusers_groups:add"), self._group_post("t48-audit-grp"))
        self.assertEqual(resp.status_code, 302)
        group = Group.objects.get(name="t48-audit-grp")
        self.assertTrue(
            group_entries(group.pk).filter(action="wagtail.create", user_id=self.admin.pk).exists()
        )

        # 组权限逐项变更 → 治理明细行（权限 codename 落 data）
        resp = client.post(
            reverse("wagtailusers_groups:edit", args=[group.pk]),
            self._group_post("t48-audit-grp", permissions=[self.add_doc_perm.pk]),
        )
        self.assertEqual(resp.status_code, 302)
        perm_row = (
            group_entries(group.pk).filter(action="peiligo.gov.group_permissions_changed").get()
        )
        self.assertEqual(perm_row.user_id, self.admin.pk)
        self.assertEqual(perm_row.data["permissions"], ["departments.add_department"])
        self.assertEqual(perm_row.data["change"], "post_add")

        # 删除组 → wagtail.delete 行保留
        resp = client.post(reverse("wagtailusers_groups:delete", args=[group.pk]), {})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            group_entries(group.pk).filter(action="wagtail.delete", user_id=self.admin.pk).exists()
        )
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_group_page_permission_change_logged(self):
        page = self.world["b_chron"]
        group = Group.objects.create(name="t48-gpp-grp")  # 独立组，避开播种 GPP
        gpp = group.page_permissions.create(
            page=page,
            permission=Permission.objects.get(
                codename="change_page", content_type__app_label="wagtailcore"
            ),
        )
        row = (
            group_entries(group.pk)
            .filter(action="peiligo.gov.group_page_permissions_changed")
            .get()
        )
        self.assertEqual(row.data["page"], page.title)
        self.assertEqual(row.data["permission"], "change_page")
        gpp.delete()
        row = (
            group_entries(group.pk)
            .filter(action="peiligo.gov.group_page_permissions_changed")
            .order_by("-pk")
            .first()
        )
        self.assertIn("移除", row.data["summary"])


class NonRequestAuditTests(TestCase):
    """无请求上下文的变更照记，但 actor 置空＋显式 non_request（§9）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_orm_membership_change_marked_non_request(self):
        user = User.objects.create_user(username="t48-orm-u", password=PASSWORD)
        user.groups.add(self.world["group_a"])  # shell/播种路径：无请求
        row = user_entries(user.pk).filter(action="peiligo.gov.membership_changed").get()
        self.assertIsNone(row.user_id, "无法归属操作者时不得伪造 actor")
        self.assertEqual(row.data["actor_type"], "non_request")

    def test_bulk_deactivate_logged(self):
        w = self.world
        client = login_client(w["admin"])
        target = User.objects.create_user(username="t48-bulk-u", password=PASSWORD)
        resp = client.post(
            reverse("wagtail_bulk_action", args=["auth", "user", "set_active_state"]),
            {"mark_as_active": "False"},  # BooleanField 合法取值；缺省即停用
            QUERY_STRING=f"id={target.pk}",
        )
        self.assertEqual(resp.status_code, 302, "批量动作应执行并回列表")
        target.refresh_from_db()
        self.assertFalse(target.is_active, "批量停用确已生效")
        row = user_entries(target.pk).filter(action="peiligo.gov.user_active_state_changed").get()
        self.assertEqual(row.user_id, w["admin"].pk)
        self.assertIn("停用", row.data["summary"])
