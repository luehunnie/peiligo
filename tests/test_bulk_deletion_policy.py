"""A3.2-IF（M3.3）批量删除动线拒删镜像测试（§17.4；PS-29；审查 F-1 修复）。

后台列表勾选删除经 ``DeleteBulkAction`` 直调 ``page.delete()``，不经
``before_delete_page``（审查 F-1 运行时实证整子树硬删）；修复挂
``before_bulk_action`` 与单页动线同一谓词拦截。四象限镜像：非空结构页
拒（整批取消）／空容器放行／内容页（叶子）不受扰／单页动线回归不破。
"""

from departments.wagtail_hooks import refuse_nonempty_structure_page_bulk_deletion
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page

from .helpers import build_sections, make_container, make_department, make_notice


def bulk_delete(client, *pages):
    """后台批量删除动线（真表单全链：勾选 id 经查询串，同审查实证口径）。"""
    url = reverse("wagtail_bulk_action", args=["wagtailcore", "page", "delete"])
    return client.post(url + "?" + "&".join(f"id={page.pk}" for page in pages))


def Page_exists(pk):
    return Page.objects.filter(pk=pk).exists()


class BulkNonemptyStructureDeletionTests(TestCase):
    """PS-29 批量动线：非空结构页拒删（与单页动线同谓词，§17.4）。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.admin = get_user_model().objects.create_superuser("admin-bk", "b@bk.test", "pw-bk")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_nonempty_section_subtree_refused(self):
        """镜像审查实证：非空板块 2 页子树＜10 无 type-to-confirm，整子树拒删。"""
        section = self.sections["chronicle"]
        container = make_container(section, self.department)
        notice = make_notice(container, slug="bulk-sec", publish=True)
        response = bulk_delete(self.client, section)
        self.assertEqual(response.status_code, 302)
        explore = reverse("wagtailadmin_explore", args=[section.get_parent().pk])
        self.assertEqual(response.url, explore)
        for page in (section, container, notice):
            self.assertTrue(Page_exists(page.pk))  # 整子树零删除（钩子取消）
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("不能删除" in m for m in texts))  # 拒因送达操作者

    def test_nonempty_container_and_home_refused(self):
        """非空容器/首页与板块同谓词拒删（三类结构页全覆盖）。"""
        container = make_container(self.sections["chronicle"], self.department)
        make_notice(container, slug="bulk-cont", publish=True)
        response = bulk_delete(self.client, container)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Page_exists(container.pk))
        home = Page.objects.get(depth=2).specific  # 站点首页（根页唯一子页）
        response = bulk_delete(self.client, home)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Page_exists(home.pk))

    def test_mixed_batch_whole_action_cancelled(self):
        """同批混入非空结构页：整个动作取消，批内其余页面零连带删除。"""
        section = self.sections["events"]  # 批内结构页（其下挂容器即非空）
        container = make_container(section, self.department)
        # 批内合法内容页（另挂纪事板块容器，§1.4 白名单）：单独成批本可删
        chronicle_container = make_container(self.sections["chronicle"], self.department)
        notice = make_notice(chronicle_container, slug="bulk-mix", publish=True)
        response = bulk_delete(self.client, notice, section)
        self.assertEqual(response.status_code, 302)
        for page in (section, container, notice):
            self.assertTrue(Page_exists(page.pk))  # 批内全部存活（事务内取消）

    def test_empty_container_bulk_delete_allowed(self):
        """空容器批量删除放行（PS-29 另半边，与单页动线口径一致）。"""
        container = make_container(self.sections["chronicle"], self.department)
        response = bulk_delete(self.client, container)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Page_exists(container.pk))

    def test_content_pages_bulk_delete_unaffected(self):
        """内容页（叶子）批量删除不受扰（§17.2/§17.3 净除动线照常）。"""
        container = make_container(self.sections["chronicle"], self.department)
        notice_a = make_notice(container, slug="bulk-na", publish=True)
        notice_b = make_notice(container, slug="bulk-nb", publish=True)
        response = bulk_delete(self.client, notice_a, notice_b)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Page_exists(notice_a.pk))
        self.assertFalse(Page_exists(notice_b.pk))
        self.assertTrue(Page_exists(container.pk))  # 容器不在批内，零波及

    def test_non_delete_bulk_actions_not_intercepted(self):
        """仅拦 delete：非删除类批量动作对同一批对象原样放行。"""
        make_container(self.sections["materials"], self.department)  # 即便非空
        result = refuse_nonempty_structure_page_bulk_deletion(
            None, "publish", [self.sections["materials"]], None
        )
        self.assertIsNone(result)  # 谓词外动作不触拒删响应

    def test_single_page_flow_regression(self):
        """单页删除动线回归：非空容器仍被拒（共用谓词经重构不改行为）。"""
        container = make_container(self.sections["chronicle"], self.department)
        make_notice(container, slug="bulk-single", publish=True)
        response = self.client.post(reverse("wagtailadmin_pages:delete", args=[container.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Page_exists(container.pk))
        self.assertTrue(Page_exists(container.get_children().first().pk))
