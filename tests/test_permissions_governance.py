"""T10–T13 治理面越权测试（M4.3 t16 迁移；矩阵 §6）。

纵向提权面：治理类 Snippet 全零权限（T10/M-D1–M-D4、N06、N07——
ADR-0004 决策 3 的执行验证）、站点设置（T11/M-E1、N03）、用户与组管理
含自我提权（T12/M-G1、M-G4、N04）、媒体集合边界（T13/M-F1–M-F4、N08）。
拒绝以零库变更快照为主证（§6 通用拒绝断言）。
"""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from wagtail.images.models import Image
from wagtail.models import Page

from .permission_helpers import (
    build_permission_world,
    denied_get,
    denied_post,
    login_client,
    png_bytes,
)

# (snippet URL 名, 标签, 新建表单数据, world 键)
SNIPPET_TARGETS = [
    (
        "departments_department",
        "部门词表",
        {"name": "越权部门", "slug": "hijack-dept", "sort_order": "9", "is_active": "on"},
        "dept_a",
    ),
    ("notices_tag", "受控标签", {"name": "越权标签", "slug": "hijack-tag"}, "tag"),
    ("resources_discipline", "学科词表", {"name": "越权学科", "sort_order": "9"}, "discipline"),
    (
        "resources_materialtype",
        "资料类型词表",
        {"name": "越权资料类型", "sort_order": "9"},
        "material_type",
    ),
    ("resources_platform", "适用平台词表", {"name": "越权平台", "sort_order": "9"}, "platform"),
    (
        "guides_guidecategory",
        "指南类别词表",
        {"name": "越权指南类别", "sort_order": "9"},
        "guide_category",
    ),
]


class T10SnippetGovernanceTests(TestCase):
    """T10 · 越权 · 治理类 Snippet 全零权限（模型级权限只授总管理员组）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_all_snippet_surfaces_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        for url_model, label, add_data, obj_key in SNIPPET_TARGETS:
            target = w[obj_key]
            with self.subTest(snippet=label):
                denied_get(
                    self, client, reverse(f"wagtailsnippets_{url_model}:list"), f"{label}列表"
                )
                add_url = reverse(f"wagtailsnippets_{url_model}:add")
                denied_get(self, client, add_url, f"{label}新建表单")
                denied_post(self, client, add_url, add_data, msg=f"新建{label}")
                edit_url = reverse(f"wagtailsnippets_{url_model}:edit", args=[target.pk])
                denied_get(self, client, edit_url, f"编辑{label}既有项")
                denied_post(
                    self,
                    client,
                    edit_url,
                    {**add_data, "name": add_data["name"] + "（越权改）"},
                    msg=f"改{label}既有项",
                )
                denied_post(
                    self,
                    client,
                    reverse(f"wagtailsnippets_{url_model}:delete", args=[target.pk]),
                    {},
                    msg=f"删{label}既有项",
                )

    def test_featured_item_surfaces_denied(self):
        """FeaturedItem（首页推荐位/置顶，N06）。"""
        w = self.world
        client = login_client(w["user_a"])
        add_url = reverse("wagtailsnippets_home_featureditem:add")
        denied_get(self, client, reverse("wagtailsnippets_home_featureditem:list"), "推荐位列表")
        denied_get(self, client, add_url, "推荐位新建表单")
        denied_post(
            self,
            client,
            add_url,
            {
                "content": str(w["page_b_draft"].pk),
                "start_at": "2026-12-01 09:00",
                "end_at": "2026-12-31 09:00",
                "enabled": "on",
            },
            msg="新建推荐位（置顶，N06）",
        )


class T11SiteSettingsTests(TestCase):
    """T11 · 越权 · 站点设置直达（M-E1/N03；URL pk 是 Site 的 pk，§3.6）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_settings_get_post_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        url = reverse("wagtailsettings:edit", args=["home", "sitesettings", w["site"].pk])
        denied_get(self, client, url, "设置编辑 URL")
        denied_post(
            self,
            client,
            url,
            {
                "alert_text": "越权紧急提示",
                "alert_start_at": "",
                "alert_end_at": "",
                "feedback_email": "hijack@example.com",
                "redirect_notice_text": "",
            },
            msg="改紧急提示与反馈邮箱（N03）",
        )
        w["site_settings"].refresh_from_db()
        self.assertNotEqual(w["site_settings"].feedback_email, "hijack@example.com")


class T12UserAndGroupAdminTests(TestCase):
    """T12 · 越权 · 用户与组管理（M-G1/M-G4/N04；含自我提权尝试）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_user_list_and_create_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        denied_get(self, client, reverse("wagtailusers_users:index"), "用户列表")
        denied_post(
            self,
            client,
            reverse("wagtailusers_users:add"),
            {
                "username": "hijack-user",
                "email": "hijack@example.com",
                "first_name": "越权",
                "last_name": "账号",
                "password1": "hijack-pw-12345",
                "password2": "hijack-pw-12345",
            },
            msg="新建用户（N04）",
        )

    def test_self_escalation_denied(self):
        """编辑自己档案把自己加入总管理员组——组归属零变更（无自我提权通道）。"""
        w = self.world
        client = login_client(w["user_a"])
        url = reverse("wagtailusers_users:edit", args=[w["user_a"].pk])
        denied_get(self, client, url, "编辑自己用户档案")
        denied_post(
            self,
            client,
            url,
            {
                "username": w["user_a"].username,
                "email": "a@example.com",
                "first_name": "部门A",
                "last_name": "岗位",
                "groups": [str(w["group_admins"].pk)],
                "password1": "",
                "password2": "",
            },
            msg="把自己加入总管理员组",
        )
        w["user_a"].refresh_from_db()
        self.assertEqual(
            list(w["user_a"].groups.values_list("name", flat=True)),
            ["dept-jwc-a"],
            "组归属零变更",
        )

    def test_group_edit_denied(self):
        """直达组编辑 URL 改权限挂载（部门组/总管理员组两靶）。"""
        w = self.world
        client = login_client(w["user_a"])
        for group in (w["group_a"], w["group_admins"]):
            with self.subTest(group=group.name):
                url = reverse("wagtailusers_groups:edit", args=[group.pk])
                denied_get(self, client, url, f"编辑组「{group.name}」")
                denied_post(
                    self,
                    client,
                    url,
                    {
                        "name": group.name,
                        "page_permissions-TOTAL_FORMS": "0",
                        "page_permissions-INITIAL_FORMS": "0",
                        "page_permissions-MIN_NUM_FORMS": "0",
                        "page_permissions-MAX_NUM_FORMS": "1000",
                        "collection_permissions-TOTAL_FORMS": "0",
                        "collection_permissions-INITIAL_FORMS": "0",
                        "collection_permissions-MIN_NUM_FORMS": "0",
                        "collection_permissions-MAX_NUM_FORMS": "1000",
                    },
                    msg=f"改组「{group.name}」权限挂载（GPP 零变更）",
                )


class T13CollectionBoundaryTests(TestCase):
    """T13 · 越权+正向 · 媒体集合边界（M-F1–M-F4/N08）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def setUp(self):
        # 上传动线写真文件——MEDIA_ROOT 指向临时目录，不入仓库 media/
        self._media_tmp = tempfile.mkdtemp(prefix="t44-media-")
        override = override_settings(MEDIA_ROOT=self._media_tmp)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self._media_tmp, ignore_errors=True)

    def test_upload_to_own_collection_allowed(self):
        """① 正向：向本部门集合上传（M-F1）。"""
        w = self.world
        client = login_client(w["user_a"])
        upload = SimpleUploadedFile("a.png", png_bytes(), content_type="image/png")
        resp = client.post(
            reverse("wagtailimages:add"),
            {"title": "A集合素材", "collection": str(w["coll_a"].pk), "file": upload},
        )
        img = Image.objects.filter(title="A集合素材").first()
        self.assertIsNotNone(img, f"上传成功 HTTP {resp.status_code}（M-F1）")
        self.assertEqual(img.collection_id, w["coll_a"].pk)
        self.assertEqual(img.uploaded_by_user_id, w["user_a"].id)

    def test_upload_to_b_collection_confined_to_own(self):
        """② 构造 POST 向 B 集合上传：请求的集合 pk 不被采纳（强制归位机制，
        M4.3 报告 ④-5）——B 集合零变更、新增素材全落回 A（N08 边界成立）。"""
        w = self.world
        client = login_client(w["user_a"])
        before_b = set(Image.objects.filter(collection=w["coll_b"]).values_list("id", flat=True))
        upload = SimpleUploadedFile("a-hijack.png", png_bytes(), content_type="image/png")
        resp = client.post(
            reverse("wagtailimages:add"),
            {"title": "越权B集合素材", "collection": str(w["coll_b"].pk), "file": upload},
        )
        after_b = set(Image.objects.filter(collection=w["coll_b"]).values_list("id", flat=True))
        self.assertEqual(before_b, after_b, "B 集合零变更（N08）")
        new_titles = {i.title: i for i in Image.objects.filter(title="越权B集合素材")}
        self.assertTrue(
            all(i.collection_id == w["coll_a"].pk for i in new_titles.values()),
            f"HTTP {resp.status_code}：新增素材全落回集合 A（唯一授权集合强制归位）",
        )

    def test_edit_b_image_denied(self):
        """③ 编辑 B 集合内素材。"""
        w = self.world
        client = login_client(w["user_a"])
        denied_post(
            self,
            client,
            reverse("wagtailimages:edit", args=[w["img_b"].pk]),
            {"title": "越权改B素材", "collection": str(w["coll_b"].pk)},
            msg="编辑 B 集合内素材",
        )

    def test_collection_management_denied(self):
        """④ 集合结构管理：新建/改名移动/删除全拒（M-F4）。"""
        w = self.world
        client = login_client(w["user_a"])
        denied_post(
            self,
            client,
            reverse("wagtailadmin_collections:add"),
            {"name": "越权集合"},
            msg="新建集合",
        )
        denied_post(
            self,
            client,
            reverse("wagtailadmin_collections:edit", args=[w["coll_b"].pk]),
            {"name": "越权改B集合"},
            msg="改名/移动 B 集合",
        )
        denied_post(
            self,
            client,
            reverse("wagtailadmin_collections:delete", args=[w["coll_b"].pk]),
            {},
            msg="删除 B 集合",
        )


class GuardPrivilegeBoundaryTests(TestCase):
    """守卫特权判定的边界（§3.4 fail-closed 语义的直证）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_tech_group_member_still_denied(self):
        """技术维护组成员不获删除面（矩阵 §3.2：R3 无 CMS 权限——组是零权限
        占位，不进守卫特权判定）。"""
        from departments.permissions import is_privileged

        w = self.world
        tech = get_user_model().objects.create_user("t44-tech", password="tech-pw-12345")
        tech.groups.add(Group.objects.get(name="技术维护"))
        self.assertFalse(is_privileged(tech))
        client = Client()
        self.assertTrue(client.login(username="t44-tech", password="tech-pw-12345"))
        before_id = w["page_b_draft"].pk
        resp = client.post(reverse("wagtailadmin_pages:delete", args=[before_id]), {})
        self.assertTrue(Page.objects.filter(pk=before_id).exists(), "技术维护成员删除被拒")
        self.assertIn(resp.status_code, (200, 302))
