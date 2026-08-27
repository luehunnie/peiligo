"""M4.4 权限骨架初始化命令测试（init_permissions；矩阵 §3.2/§3.6）。

验证命令产出的组配置恰为矩阵 §3.2 配置表形态（M4.2 PoC CHECK1 的
正式化），以及幂等可重复、默认组清理与口令纪律（env/stdin、无默认口令）。
"""

import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from home.models import SectionPage
from wagtail.models import (
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
    Page,
)

from .helpers import build_sections, make_container, make_department
from .permission_helpers import build_permission_world


def run_init(**kwargs):
    out = StringIO()
    call_command("init_permissions", stdout=out, **kwargs)
    return out.getvalue()


class InitPermissionsCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.dept = make_department("教务处", "jwc")
        cls.container = make_container(cls.sections["chronicle"], cls.dept)

    def test_admin_group_skeleton(self):
        """总管理员组：根级 GPP(add/change/publish)＋全量模型权限＋GCP@根集合。"""
        run_init()
        group = Group.objects.get(name="总管理员")
        root = Page.get_first_root_node()
        codenames = set(
            GroupPagePermission.objects.filter(group=group).values_list(
                "permission__codename", flat=True
            )
        )
        self.assertEqual(codenames, {"add_page", "change_page", "publish_page"})
        self.assertTrue(
            GroupPagePermission.objects.filter(group=group, page=root).exists(),
            "根级挂载（全树传播锚点）",
        )
        # 全量模型权限（含非叶/批量删除所需 bulk_delete_page）
        self.assertEqual(group.permissions.count(), Permission.objects.count())
        self.assertTrue(
            group.permissions.filter(codename="bulk_delete_page").exists(),
            "bulk_delete_page 在位（矩阵 §3.2 R1 行）",
        )
        # GCP@根集合：集合治理只认 GCP 记录（A4.2 PoC 发现 3）
        root_collection = Collection.get_first_root_node()
        gcp = set(
            GroupCollectionPermission.objects.filter(group=group).values_list(
                "permission__content_type__app_label",
                "permission__codename",
            )
        )
        self.assertEqual(
            gcp,
            {
                ("wagtailcore", "add_collection"),
                ("wagtailcore", "change_collection"),
                ("wagtailimages", "add_image"),
                ("wagtailimages", "change_image"),
            },
        )
        self.assertTrue(
            GroupCollectionPermission.objects.filter(
                group=group, collection=root_collection
            ).exists()
        )

    def test_tech_group_zero_permissions(self):
        """技术维护组：零权限占位（矩阵 §3.2 R3 无 CMS 权限；入组不获任何面）。"""
        run_init()
        group = Group.objects.get(name="技术维护")
        self.assertEqual(group.permissions.count(), 0)
        self.assertEqual(group.page_permissions.count(), 0)
        self.assertEqual(group.collection_permissions.count(), 0)
        self.assertFalse(
            group.permissions.filter(codename="access_admin").exists(),
            "连后台入口权限也无（R3 排障走运维通道，非 CMS）",
        )

    def test_dept_group_skeleton(self):
        """部门组：GPP(add/change/publish)@容器＋Django 权限恰一枚 access_admin＋GCP@部门集合。"""
        run_init()
        group = Group.objects.get(name="dept-jwc")
        self.assertEqual(
            sorted(group.permissions.values_list("codename", flat=True)),
            ["access_admin"],
            "Django 权限恰一枚（矩阵 §3.6 实测形态）",
        )
        gpp = set(
            GroupPagePermission.objects.filter(group=group).values_list(
                "page_id", "permission__codename"
            )
        )
        self.assertEqual(
            gpp,
            {
                (self.container.pk, "add_page"),
                (self.container.pk, "change_page"),
                (self.container.pk, "publish_page"),
            },
        )
        # 部门集合自动建立并挂 GCP(add/change_image)
        collection = Collection.objects.get(name="教务处")
        gcp = set(
            GroupCollectionPermission.objects.filter(group=group).values_list(
                "permission__codename", flat=True
            )
        )
        self.assertEqual(gcp, {"add_image", "change_image"})
        self.assertEqual(
            GroupCollectionPermission.objects.filter(group=group, collection=collection).count(),
            2,
        )

    def test_idempotent_rerun_converges(self):
        """幂等：重复执行零重复挂载、零删除既有数据（可重复执行）。"""
        run_init()
        snapshot = {
            "gpp": GroupPagePermission.objects.count(),
            "gcp": GroupCollectionPermission.objects.count(),
            "groups": list(Group.objects.values_list("name", flat=True)),
            "collections": list(Collection.objects.values_list("name", flat=True)),
            "pages": Page.objects.count(),
        }
        run_init()
        self.assertEqual(GroupPagePermission.objects.count(), snapshot["gpp"])
        self.assertEqual(GroupCollectionPermission.objects.count(), snapshot["gcp"])
        self.assertEqual(list(Group.objects.values_list("name", flat=True)), snapshot["groups"])
        self.assertEqual(
            list(Collection.objects.values_list("name", flat=True)), snapshot["collections"]
        )
        self.assertEqual(Page.objects.count(), snapshot["pages"])

    def test_new_container_attached_on_rerun(self):
        """可重复：后续新建的容器在重跑时补挂 GPP（收敛到期望配置）。"""
        run_init()
        second = make_container(self.sections["materials"], self.dept)
        run_init()
        pages = set(
            GroupPagePermission.objects.filter(group__name="dept-jwc")
            .values_list("page_id", flat=True)
            .distinct()
        )
        self.assertEqual(pages, {self.container.pk, second.pk})

    def test_prunes_default_editor_moderator_groups(self):
        """清理迁移自动创建的空默认组 Editors/Moderators（M4.3 报告 ④-6）。"""
        self.assertTrue(Group.objects.filter(name="Editors").exists(), "迁移期默认组在场")
        run_init()
        self.assertFalse(Group.objects.filter(name="Editors").exists())
        self.assertFalse(Group.objects.filter(name="Moderators").exists())

    def test_prune_keeps_default_group_with_members(self):
        """有成员的默认组保留并告警（不静默动既有账号归属）。"""
        editors = Group.objects.get(name="Editors")
        user = get_user_model().objects.create_user("legacy-editor", password="pw-x")
        editors.user_set.add(user)
        output = run_init()
        self.assertTrue(Group.objects.filter(pk=editors.pk).exists())
        self.assertIn("已有成员", output)

    def test_account_creation_requires_password_source(self):
        """口令纪律：无 --password-stdin/环境变量即拒绝创建（不落默认口令）。"""
        with self.assertRaises(CommandError):
            run_init(admin_user="admin-x")
        self.assertFalse(get_user_model().objects.filter(username="admin-x").exists())

    def test_account_created_via_env_password(self):
        """env 口令创建账号：非 superuser、组权限行权、口令可用且零明文输出。"""
        with mock.patch.dict(os.environ, {"PEILIGO_INIT_PASSWORD": "env-pw-12345"}):
            output = run_init(admin_user="admin-env")
        user = get_user_model().objects.get(username="admin-env")
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["总管理员"])
        self.assertNotIn("env-pw-12345", output, "口令零明文输出")
        self.assertTrue(user.check_password("env-pw-12345"))

    def test_account_created_via_stdin_password(self):
        """stdin 口令创建部门岗位账号：入本部门组、口令可登录。"""
        with mock.patch("sys.stdin", StringIO("stdin-pw-67890\n")):
            run_init(dept_user="jwc-post", department="jwc", password_stdin=True)
        user = get_user_model().objects.get(username="jwc-post")
        self.assertFalse(user.is_superuser)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["dept-jwc"])
        self.assertTrue(user.check_password("stdin-pw-67890"))
        from django.test import Client

        client = Client()
        self.assertTrue(client.login(username="jwc-post", password="stdin-pw-67890"))

    def test_empty_stdin_password_refused(self):
        """stdin 空行＝未提供口令：拒绝创建（不产生空口令账号）。"""
        with mock.patch("sys.stdin", StringIO("\n")):
            with self.assertRaises(CommandError):
                run_init(admin_user="admin-empty")
        self.assertFalse(get_user_model().objects.filter(username="admin-empty").exists())

    def test_second_dept_account_refused(self):
        """每部门至多一个岗位账号（PRD §4.3）：部门组已有成员即拒绝。"""
        with mock.patch("sys.stdin", StringIO("first-pw-12345\n")):
            run_init(dept_user="jwc-first", department="jwc", password_stdin=True)
        with mock.patch("sys.stdin", StringIO("second-pw-12345\n")):
            with self.assertRaises(CommandError):
                run_init(dept_user="jwc-second", department="jwc", password_stdin=True)
        self.assertFalse(get_user_model().objects.filter(username="jwc-second").exists())

    def test_second_admin_account_skipped(self):
        """V1 恰一个 R1 账号（PRD §4.2）：总管理员组已有成员则告警跳过。"""
        with mock.patch.dict(os.environ, {"PEILIGO_INIT_PASSWORD": "adm-pw-12345"}):
            run_init(admin_user="admin-one")
            output = run_init(admin_user="admin-two")
        self.assertFalse(get_user_model().objects.filter(username="admin-two").exists())
        self.assertIn("恰一个", output)


class WorldScaffoldSanityTests(TestCase):
    """权限测试世界脚手架自检（build_permission_world 的组形态）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_world_dept_groups_isolated(self):
        """A/B 两组 GPP 恰各挂自己容器（横向隔离的锚点面）。"""
        a_pages = set(
            GroupPagePermission.objects.filter(group=self.world["group_a"])
            .values_list("page_id", flat=True)
            .distinct()
        )
        b_pages = set(
            GroupPagePermission.objects.filter(group=self.world["group_b"])
            .values_list("page_id", flat=True)
            .distinct()
        )
        self.assertEqual(a_pages, {c.pk for c in self.world["a_containers"].values()})
        self.assertEqual(b_pages, {self.world["b_chron"].pk, self.world["b_mat"].pk})
        self.assertFalse(a_pages & b_pages)

    def test_world_section_pages_untouched_by_dept_groups(self):
        """板块页/首页不在部门组授权范围（矩阵 §3.2：权限仅挂容器节点）。"""
        section_ids = {s.pk for s in SectionPage.objects.all()}
        home = Page.objects.get(depth=2).pk
        for group in (self.world["group_a"], self.world["group_b"]):
            pages = set(
                GroupPagePermission.objects.filter(group=group).values_list("page_id", flat=True)
            )
            self.assertFalse(pages & section_ids)
            self.assertNotIn(home, pages)
