"""L-9（Final Fix）：批量移动动线内容模型守卫行为测试。

后台列表勾选移动经 ``MoveBulkAction`` 直调 ``page.move()``，不经
``before_move_page``——修复后与单页动线共用 ``_move_violation`` 规则核心
（§1.4 板块合法性/§4 部门一致性/子树复检），任一违规整批取消。
单页动线既有回归见 ``test_content_tree.MoveHookTests``（直调钩子）。
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from wagtail.models import PageLogEntry

from .helpers import make_material, make_notice
from .permission_helpers import (
    PASSWORD,
    build_permission_world,
    login_client,
    permission_snapshot,
    snapshot_diff,
)


def bulk_move(client, destination, *pages):
    """后台批量移动动线（勾选 id 经查询串，目的地经 chooser 表单字段）。"""
    url = reverse("wagtail_bulk_action", args=["wagtailcore", "page", "move"])
    url += "?" + "&".join(f"id={page.pk}" for page in pages)
    return client.post(url, {"chooser": str(destination.pk)})


def parent_of(page):
    return page.get_parent().specific


class BulkMovePolicyTests(TestCase):
    """批量移动守卫：合法放行、板块合法性、部门一致性与子树复检。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        cls.superuser = get_user_model().objects.create_superuser(
            "bulk-move-admin", "bm@t.test", PASSWORD
        )
        # A 部门纪事容器内一封通知（无活动字段＝纪事合法形态）
        cls.a_notice = make_notice(cls.world["a_containers"]["chronicle"], slug="bm-a-notice")
        # A 部门资料容器内一份资料（materials 板块专用类型）
        cls.a_material = make_material(cls.world["a_containers"]["materials"], slug="bm-a-material")

    def test_r2_legal_same_container_move_allowed(self):
        """R2 同部门合法移动（同容器重排，规则平凡通过）→ 放行并落 wagtail.move。

        §4 同板块每部门恰一容器约束下不存在跨容器合法同部门移动，
        放行面以同容器移动验证（守卫不误伤合法动线）。
        """
        w = self.world
        client = login_client(w["user_a"])
        container = w["a_containers"]["chronicle"]
        resp = bulk_move(client, container, self.a_notice)
        self.assertEqual(resp.status_code, 302)
        self.a_notice.refresh_from_db()
        self.assertEqual(parent_of(self.a_notice).pk, container.pk, "父级不变")
        # 同父重排 url_path 不变 → wagtail 记 wagtail.reorder（跨父才记 wagtail.move）
        self.assertTrue(
            PageLogEntry.objects.filter(
                page_id=self.a_notice.pk, action__in=("wagtail.move", "wagtail.reorder")
            ).exists(),
            "移动应真实发生（log 面留 move/reorder 行）",
        )

    def test_r2_cross_section_event_rule_denied(self):
        """R2 把无活动字段的通知移入校园活动容器（§7.2 活动字段必填）→ 整批取消。"""
        w = self.world
        client = login_client(w["user_a"])
        before = permission_snapshot()
        bulk_move(client, w["a_containers"]["events"], self.a_notice)
        diff = snapshot_diff(before, permission_snapshot())
        self.assertEqual(diff, "", f"预期零库变更；实际 diff：{diff}")
        self.a_notice.refresh_from_db()
        self.assertEqual(
            parent_of(self.a_notice).pk, w["a_containers"]["chronicle"].pk, "未发生移动"
        )

    def test_material_into_wrong_section_container_denied(self):
        """资料移入纪事容器（板块白名单 §1.4：materials ∉ chronicle）→ 取消。"""
        w = self.world
        client = login_client(self.superuser)
        before = permission_snapshot()
        bulk_move(client, w["a_containers"]["chronicle"], self.a_material)
        self.assertEqual(snapshot_diff(before, permission_snapshot()), "")
        self.a_material.refresh_from_db()
        self.assertEqual(parent_of(self.a_material).pk, w["a_containers"]["materials"].pk)

    def test_content_directly_under_section_denied(self):
        """内容页移到板块页下（父级非部门容器 §1.4）→ 取消。"""
        w = self.world
        client = login_client(self.superuser)
        before = permission_snapshot()
        bulk_move(client, w["sections"]["materials"], self.a_material)
        self.assertEqual(snapshot_diff(before, permission_snapshot()), "")
        self.a_material.refresh_from_db()
        self.assertEqual(parent_of(self.a_material).pk, w["a_containers"]["materials"].pk)

    def test_cross_department_move_denied(self):
        """A 部门内容移入 B 部门容器（部门一致性 §4）→ 取消。"""
        w = self.world
        client = login_client(self.superuser)
        before = permission_snapshot()
        bulk_move(client, w["b_chron"], self.a_notice)
        self.assertEqual(snapshot_diff(before, permission_snapshot()), "")
        self.a_notice.refresh_from_db()
        self.assertEqual(
            parent_of(self.a_notice).pk, w["a_containers"]["chronicle"].pk, "未发生移动"
        )

    def test_container_move_department_clash_denied(self):
        """容器移入已有同部门容器的板块（§4 一板块一容器）→ 整批取消。"""
        w = self.world
        client = login_client(self.superuser)
        container = w["a_containers"]["materials"]
        before = permission_snapshot()
        bulk_move(client, w["sections"]["events"], container)
        self.assertEqual(snapshot_diff(before, permission_snapshot()), "")
        container.refresh_from_db()
        self.assertEqual(parent_of(container).pk, w["sections"]["materials"].pk, "容器未发生移动")

    def test_container_subtree_violation_denied(self):
        """容器携子树换板块（子树通知将违反目标板块 §7.2 活动字段必填）→ 取消。

        B 部门无活动容器（无 §4 撞面），deny 须由子树复检路径触发——
        两封无活动字段的通知移入 events 板块即违约。
        """
        w = self.world
        client = login_client(self.superuser)
        container = w["b_chron"]
        before = permission_snapshot()
        bulk_move(client, w["sections"]["events"], container)
        self.assertEqual(snapshot_diff(before, permission_snapshot()), "")
        container.refresh_from_db()
        self.assertEqual(parent_of(container).pk, w["sections"]["chronicle"].pk, "容器未发生移动")
