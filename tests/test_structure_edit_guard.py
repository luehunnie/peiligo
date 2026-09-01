"""H-1（Final Fix）：结构边界页编辑守卫（矩阵 M-C3）行为测试。

首页/板块/部门容器是权限边界载体：非特权后台账号对三者编辑（含改 slug/
department 结构字段）服务端拒绝（GET/POST 同源 ``before_edit_page``），
R1/特权管理员放行，内容页编辑不受影响。拒绝主证沿用矩阵口径：零库变更
快照（title/slug/修订数/日志等），HTTP 302 仅辅证（拒权与成功同为 302）。
"""

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse
from wagtail.models import Page

from departments.models import DepartmentContainerPage
from departments.wagtail_hooks import refuse_structure_page_edit_for_non_privileged

from .permission_helpers import (
    build_permission_world,
    comment_formset_zeros,
    denied_get,
    denied_post,
    login_client,
    rev_count,
)


def container_form(title, slug, department_id):
    """容器编辑表单官方字段集（title/slug/department＋评论 formset 零值）。"""
    return {
        "title": title,
        "slug": slug,
        "department": str(department_id),
        **comment_formset_zeros(),
    }


class StructureEditGuardTests(TestCase):
    """before_edit_page 守卫：拒绝面、放行面与内容页不受扰。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_dept_user_edit_own_container_denied(self):
        """R2 编辑自己部门的容器 → 拒绝（零库变更，含 title 不可变）。"""
        w = self.world
        client = login_client(w["user_a"])
        container = w["a_containers"]["chronicle"]
        resp = denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:edit", args=[container.pk]),
            container_form("越权改名容器", container.slug, w["dept_a"].id),
            msg="R2 编辑自己容器",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            DepartmentContainerPage.objects.get(pk=container.pk).title, container.title
        )

    def test_dept_user_change_container_slug_denied(self):
        """R2 修改容器 slug（结构字段）→ 拒绝（零库变更）。"""
        w = self.world
        client = login_client(w["user_a"])
        container = w["a_containers"]["materials"]
        resp = denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:edit", args=[container.pk]),
            container_form(container.title, "jwc-a-hacked", w["dept_a"].id),
            msg="R2 改容器 slug",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            DepartmentContainerPage.objects.get(pk=container.pk).slug, container.slug
        )

    def test_dept_user_change_container_department_denied(self):
        """R2 修改容器 department 绑定（结构字段）→ 拒绝（零库变更）。"""
        w = self.world
        client = login_client(w["user_b"])
        container = w["b_chron"]
        resp = denied_post(
            self,
            client,
            reverse("wagtailadmin_pages:edit", args=[container.pk]),
            container_form(container.title, container.slug, w["dept_a"].id),
            msg="R2 改容器 department",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            DepartmentContainerPage.objects.get(pk=container.pk).department_id,
            w["dept_b"].id,
        )

    def test_dept_user_get_container_edit_form_denied(self):
        """R2 打开容器编辑表单（GET）同样拒绝（fail-closed 双动线）。"""
        w = self.world
        client = login_client(w["user_a"])
        container = w["a_containers"]["events"]
        resp = denied_get(
            self, client, reverse("wagtailadmin_pages:edit", args=[container.pk]), msg="GET 编辑容器"
        )
        self.assertEqual(resp.status_code, 302)

    def test_privileged_admin_edit_container_allowed(self):
        """R1（总管理员组，非 superuser）编辑容器放行：结构字段修改生效。

        默认 POST＝存草稿（变更落最新修订、页面记录不动）；此处以
        action-publish 发布使修改落到页面记录，可对 slug 直接断言。
        """
        w = self.world
        client = login_client(w["admin"])
        container = w["b_chron"]
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[container.pk]),
            {**container_form(container.title, "xsc-b-new", w["dept_b"].id), "action-publish": "true"},
        )
        self.assertEqual(resp.status_code, 302)
        container.refresh_from_db()
        self.assertEqual(container.slug, "xsc-b-new", "R1 改容器 slug 应生效")

    def test_guard_predicate_covers_homepage_and_section(self):
        """守卫谓词覆盖首页与板块页（直调钩子：R2 拒、R1 放）。"""
        w = self.world
        home = Page.objects.get(depth=2).specific
        section = Page.objects.get(depth=2).get_children().specific().first()
        rf = RequestFactory()
        for page in (home, section):
            for user, expect_block in ((w["user_a"], True), (w["admin"], False)):
                request = rf.get(f"/admin/pages/{page.pk}/edit/")
                request.user = user
                request.session = "session"
                request._messages = FallbackStorage(request)
                result = refuse_structure_page_edit_for_non_privileged(request, page)
                self.assertEqual(
                    result is not None,
                    expect_block,
                    f"{type(page).__name__} × {user.username} 预期拦截={expect_block}",
                )

    def test_content_page_edit_unaffected(self):
        """内容页编辑不受守卫影响：R2 编辑自己通知照常落修订。"""
        w = self.world
        client = login_client(w["user_b"])
        page = w["page_b_draft"]
        from .permission_helpers import notice_form

        before = rev_count(page.pk)
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[page.pk]),
            notice_form("B部门草稿通知（改）", "t44-b-draft", w["dept_b"].id),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(rev_count(page.pk), before + 1, "内容页编辑应照常落修订")
