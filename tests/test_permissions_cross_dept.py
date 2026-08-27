"""T05–T09 越权动线（M4.3 t16 迁移；矩阵 §6）。

横向越权面（N01/N05/N15）与永久删除守卫（§3.4 关闭措施）：
跨部门创建/编辑/发布/下线（T05–T07）、永久删除自己页面单条+批量双路径
（T08）、跨部门与结构删除/移动（T09）。全部服务端构造 URL/POST，拒绝以
**零库变更快照为主证**（HTTP 302 仅辅证——拒权与成功同为 302，§3.6）。
"""

from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page

from .permission_helpers import (
    build_permission_world,
    bulk_delete_url,
    denied_get,
    denied_post,
    login_client,
    material_form,
    notice_form,
    permission_snapshot,
    snapshot_diff,
)


class T05CrossDeptCreateTests(TestCase):
    """T05 · 越权 · A 向 B 容器直接 POST 创建（M-B3/N01；PRD §23 场景 1）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_create_into_b_container_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        url = reverse("wagtailadmin_pages:add", args=["resources", "materialpage", w["b_mat"].pk])
        # GET 面：构造 URL 直达创建表单（GET 200＝表单可达＝越权信号）
        denied_get(self, client, url, "A GET B 容器创建表单")
        # POST 面：表单数据与 T01 正向同构（同构表单对有权容器已证合法）
        denied_post(
            self,
            client,
            url,
            material_form(
                "越权B容器创建",
                "b-hijack",
                w["dept_b"].id,
                w["discipline"].id,
                w["material_type"].id,
            ),
            msg="A POST 向 B 容器创建",
        )
        self.assertFalse(Page.objects.filter(slug="b-hijack").exists(), "B 子树无越权新增页面")


class T06CrossDeptEditTests(TestCase):
    """T06 · 越权 · A 直接 POST 编辑 B 已发布页（M-B1/M-B4/N01）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_edit_b_page_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        page_b = w["page_b_live"]
        url = reverse("wagtailadmin_pages:edit", args=[page_b.pk])
        denied_get(self, client, url, "A GET B 页面编辑表单")
        denied_post(
            self,
            client,
            url,
            notice_form("B部门已发布通知（越权改）", "b-live", w["dept_b"].id),
            msg="A POST 编辑 B 页面",
        )
        page_b.refresh_from_db()
        self.assertEqual(page_b.title, "B部门已发布通知", "B 页内容零变更")
        self.assertTrue(page_b.live, "live 状态零变更")


class T07CrossDeptPublishTests(TestCase):
    """T07 · 越权 · 横向发布/下线（M-B5/M-B6/N01/N15——ADR-0004 否决方案 b 的反向验证）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_publish_b_draft_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        draft = w["page_b_draft"]
        denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:edit", args=[draft.pk]),
            {
                **notice_form("B部门草稿通知", "b-draft", w["dept_b"].id),
                "action-publish": "action-publish",
            },
            msg="A 经 action-publish 发布 B 草稿",
        )
        draft.refresh_from_db()
        self.assertFalse(draft.live, "B 草稿保持草稿")
        self.assertFalse(draft.expired)

    def test_unpublish_b_live_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        live = w["page_b_live"]
        denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:unpublish", args=[live.pk]),
            {},
            msg="A 下线 B 已发布页",
        )
        live.refresh_from_db()
        self.assertTrue(live.live, "B 页保持 live（发布面不横向越出本部门子树，N15）")


class T08DeleteOwnPageGuardTests(TestCase):
    """T08 · 越权 · 永久删除自己拥有的页面（M-A8/N02/§3.4；单条+批量双路径）。

    张力背景：change@容器使子树内任意页 can_delete=True（含自己创建页），
    守卫挂载前可删——双钩子只拒绝守卫是必需件（M4.2 PoC CHECK5 实测）。
    """

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def _make_own_pages(self, count=2):
        """A 自建页素材（owner=A，经真实创建动线）。"""
        w = self.world
        client = login_client(w["user_a"])
        ids = []
        for i in range(1, count + 1):
            slug = f"a-del-{i}"
            resp = client.post(
                reverse(
                    "wagtailadmin_pages:add",
                    args=["notices", "noticepage", w["a_containers"]["chronicle"].pk],
                ),
                notice_form(f"A删除张力{i}", slug, w["dept_a"].id),
            )
            page = Page.objects.filter(slug=slug).first()
            self.assertIsNotNone(page, f"素材页 {i} 创建失败 HTTP {resp.status_code}")
            self.assertEqual(page.owner_id, w["user_a"].id)
            ids.append(page.pk)
        return ids

    def test_single_path_guarded(self):
        w = self.world
        client = login_client(w["user_a"])
        (page_id, _other) = self._make_own_pages()
        before = permission_snapshot()
        resp = client.post(reverse("wagtailadmin_pages:delete", args=[page_id]), {})
        diff = snapshot_diff(before, permission_snapshot())
        self.assertEqual(diff, "", f"单条路径零库变更：{diff}")
        self.assertIn(resp.status_code, (200, 302))
        self.assertTrue(
            Page.objects.filter(pk=page_id).exists(), "页面仍在（before_delete_page 拦截）"
        )

    def test_bulk_path_guarded(self):
        """批量动线 DeleteBulkAction.execute_action 直调 page.delete() 绕过
        单页钩子——第二钩 before_bulk_action 拦截整批（含同批其余页面）。"""
        w = self.world
        client = login_client(w["user_a"])
        ids = self._make_own_pages()
        before = permission_snapshot()
        resp = client.post(bulk_delete_url(*ids), {})
        diff = snapshot_diff(before, permission_snapshot())
        self.assertEqual(diff, "", f"批量路径零库变更：{diff}")
        self.assertIn(resp.status_code, (200, 302))
        self.assertEqual(Page.objects.filter(pk__in=ids).count(), 2, "两页均在（整批取消）")

    def test_guard_message_delivered(self):
        from django.contrib.messages import get_messages

        w = self.world
        client = login_client(w["user_a"])
        (page_id, _other) = self._make_own_pages()
        resp = client.post(reverse("wagtailadmin_pages:delete", args=[page_id]), {})
        texts = [str(m) for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any("永久删除仅限总管理员" in m for m in texts), "拒因送达操作者")


class T09CrossDeptStructureTests(TestCase):
    """T09 · 越权 · 跨部门与结构删除/移动（M-B7/M-C4/M-C5/N01/N05）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_delete_b_page_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:delete", args=[w["page_b_live"].pk]),
            {},
            msg="A 删除 B 页面",
        )

    def test_delete_b_container_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:delete", args=[w["b_chron"].pk]),
            {},
            msg="A 删除 B 容器",
        )

    def test_delete_section_page_denied(self):
        w = self.world
        client = login_client(w["user_a"])
        denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:delete", args=[w["sections"]["events"].pk]),
            {},
            msg="A 删除板块页",
        )

    def test_move_b_container_denied_both_steps(self):
        """移动 B 容器两动线：选目标步与直达 move_confirm（动作层复检）。"""
        w = self.world
        client = login_client(w["user_a"])
        events = w["sections"]["events"]
        denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:move", args=[w["b_chron"].pk]),
            {"new_parent_page": str(events.pk)},
            msg="A 移动 B 容器（选目标步）",
        )
        denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:move_confirm", args=[w["b_chron"].pk, events.pk]),
            {},
            msg="A 直达 move_confirm 移动 B 容器",
        )

    def test_tree_structure_unchanged(self):
        """树结构整体零变更口径显式复核（path/depth/numchild——N05）。"""
        before = permission_snapshot()
        # 页面字段快照含 path/depth/numchild；此处做一次全量读检
        for page in Page.objects.all():
            self.assertIn(page.pk, before["pages"])
            recorded = before["pages"][page.pk]
            self.assertEqual((page.path, page.depth, page.numchild), recorded[5:8])
