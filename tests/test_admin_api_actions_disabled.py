"""Admin API 页面 action 端点禁用（终审 Reviewer A：HTML 守卫一致性收口）。

需求：HTML Admin 守卫钩子（before_edit_page/before_delete_page/
before_move_page/before_bulk_action 承载的 H-1/M4/L-9/§17.4 治理）不得被
/admin/api/main/pages/<id>/action/<name>/ 端点旁路。Wagtail 7.4.2 源码
亲证：action_view（wagtail/admin/api/views.py）无 permission_classes
（项目未配置 REST_FRAMEWORK，DRF 缺省 AllowAny），无页面级权限检查，径直
执行核心 wagtail.actions.*，不经任何 before_*_page 钩子（钩子仅挂 HTML
动线 wagtail/admin/views/pages/*.py）；唯一屏障是 Wagtail 树权限，而
change@容器 GPP 附带 can_delete/can_publish（departments/wagtail_hooks
M4.4 注）——R2 经 API 即可永久删除自己子树内容（M4 面）、发布/回滚容器
修订（H-1 结构边界面），§17.4/L-9/递归复制的内容模型复检对 API 无钩子
可用。

后台前端零依赖该 action 面（全部编译 bundle 无 action/ 引用；仅
sidebar.js 消费 GET listing，可达性由既有
test_permissions_admin_boundary.test_browser_tree_api_reachable 钉住），
按收口令优先方案整体禁用（construct_admin_api 官方扩展点替换 pages 端点
viewset）——治理语义单一来源仍是 HTML 守卫钩子，不新增第二套权限判断。

断言口径沿用矩阵 §3.6：拒绝以零库变更快照为主证（denied_post），HTTP
404 仅辅证。
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from wagtail.models import Page

from .permission_helpers import (
    PASSWORD,
    build_permission_world,
    denied_post,
    login_client,
    permission_snapshot,
    snapshot_diff,
)

# PagesAdminAPIViewSet.actions 全集（wagtail/admin/api/views.py）
ACTION_NAMES = (
    "convert_alias",
    "copy",
    "delete",
    "publish",
    "unpublish",
    "move",
    "copy_for_translation",
    "create_alias",
    "revert_to_page_revision",
)


def action_url(page, action):
    return f"/admin/api/main/pages/{page.id}/action/{action}/"


class AdminAPIPageActionDisabledTests(TestCase):
    """action 端点对一切账号禁用：拒绝零库变更；GET 读写面不回退。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_r2_delete_own_content_via_api_disabled(self):
        """M4 面：R2 经 API 永久删除自己部门内容 → 404＋零库变更。"""
        w = self.world
        client = login_client(w["user_b"])
        resp = denied_post(
            self,
            client,
            action_url(w["page_b_live"], "delete"),
            {},
            msg="R2 经 API 永久删除自己内容",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Page.objects.filter(id=w["page_b_live"].id).exists(), "页面不得消失")

    def test_r2_publish_and_revert_container_via_api_disabled(self):
        """H-1 结构边界面：R2 对自己容器 publish/revert → 404＋零库变更。"""
        w = self.world
        client = login_client(w["user_b"])
        container = w["b_chron"]
        revision = container.save_revision(user=w["user_b"])
        resp = denied_post(
            self, client, action_url(container, "publish"), {}, msg="R2 经 API 发布容器"
        )
        self.assertEqual(resp.status_code, 404)
        resp = denied_post(
            self,
            client,
            action_url(container, "revert_to_page_revision"),
            {"revision_id": revision.id},
            msg="R2 经 API 回滚容器修订",
        )
        self.assertEqual(resp.status_code, 404)

    def test_r2_move_via_api_disabled(self):
        """L-9 面：R2 经 API 移动自己内容到本部门另一容器 → 404＋零库变更。"""
        w = self.world
        client = login_client(w["user_b"])
        resp = denied_post(
            self,
            client,
            action_url(w["page_b_live"], "move"),
            # position 缺省时 parent_after＝target 父级（板块页，R2 无权）；
            # 显式 last-child 才是真实越权形态（destination 即容器本身）。
            {"destination_page_id": w["b_mat"].id, "position": "last-child"},
            msg="R2 经 API 移动自己内容",
        )
        self.assertEqual(resp.status_code, 404)

    def test_r1_delete_via_api_disabled(self):
        """API 非产品动线：R1 特权账号同禁，治理动线收敛回 HTML Admin。"""
        w = self.world
        client = login_client(w["admin"])
        resp = denied_post(
            self,
            client,
            action_url(w["page_b_live"], "delete"),
            {},
            msg="R1 经 API 删除页面",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Page.objects.filter(id=w["page_b_live"].id).exists(), "页面不得消失")

    def test_anonymous_and_r3_action_post_disabled(self):
        """匿名与零权限账号（R3 型）POST action 端点 → 302 登录跳转＋零库变更。

        action 路由已注销，URL 落入 admin 兜底 ``^.*/$``（home.default，
        require_admin_access 装饰）：未认证一律 302 登录页——Wagtail 后台
        对一切未匹配 URL 的标准行为，无任何 action 执行面；已认证账号同
        URL 由同一兜底给 404（其余用例已覆盖）。
        """
        w = self.world
        r3 = get_user_model().objects.create_user("t44-api-r3", password=PASSWORD)
        before = permission_snapshot()  # 基线含本用例夹具（R3 账号）自身
        resp = Client().post(action_url(w["page_b_live"], "delete"), {})
        self.assertEqual(resp.status_code, 302, "匿名 POST 落 admin 兜底→登录跳转")
        resp = login_client(r3).post(action_url(w["page_b_live"], "delete"), {})
        self.assertEqual(resp.status_code, 302, "R3 型 POST 落 admin 兜底→登录跳转")
        diff = snapshot_diff(before, permission_snapshot())
        self.assertEqual(diff, "", f"预期零库变更；实际 diff：{diff}")

    def test_recursive_container_copy_via_api_disabled(self):
        """before_copy_page 面：递归复制容器跨板块 → 404＋零库变更。"""
        w = self.world
        client = login_client(w["admin"])
        resp = denied_post(
            self,
            client,
            action_url(w["b_chron"], "copy"),
            {"recursive": True, "destination_page_id": w["sections"]["materials"].id},
            msg="递归复制容器跨板块",
        )
        self.assertEqual(resp.status_code, 404)

    def test_all_action_names_disabled_for_r2(self):
        """九个 action 名全量扫描：R2 一律 404，零库变更。"""
        w = self.world
        client = login_client(w["user_b"])
        payloads = {
            "convert_alias": {},
            "copy": {"recursive": False},
            "delete": {},
            "publish": {},
            "unpublish": {"recursive": True},
            "move": {"destination_page_id": w["b_mat"].id, "position": "last-child"},
            "copy_for_translation": {},
            "create_alias": {"recursive": False},
            "revert_to_page_revision": {"revision_id": 1},
        }
        before = permission_snapshot()
        for action in ACTION_NAMES:
            resp = client.post(action_url(w["page_b_live"], action), payloads[action])
            self.assertEqual(resp.status_code, 404, f"action={action} 不得可达")
        diff = snapshot_diff(before, permission_snapshot())
        self.assertEqual(diff, "", f"预期零库变更；实际 diff：{diff}")

    def test_listing_and_detail_still_reachable_for_r2(self):
        """正向对照：sidebar 依赖的 GET listing/detail 保持可达（不误伤读面）。

        Wagtail 7.4.3（PYSEC-2026-3939 修复）将 listing 查询集收窄为
        explorable_instances(user)：可达性探针须落在用户可浏览范围内
        （此处取部门 B 自己的容器）；越界父节点（root）如今按设计返回
        400 "parent page doesn't exist"，一并断言为回归守卫。
        """
        w = self.world
        client = login_client(w["user_b"])
        resp = client.get("/admin/api/main/pages/", {"child_of": w["b_chron"].id})
        self.assertEqual(resp.status_code, 200)
        resp = client.get(f"/admin/api/main/pages/{w['page_b_live'].id}/")
        self.assertEqual(resp.status_code, 200)
        # 越界探针（root 不在可浏览集内）→ 400，权限边界按设计收口。
        root_id = Page.get_first_root_node().id
        resp = client.get("/admin/api/main/pages/", {"child_of": root_id})
        self.assertEqual(resp.status_code, 400)
