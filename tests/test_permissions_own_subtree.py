"""T01–T04 正向动线（M4.3 t16 迁移；矩阵 §6）。

部门岗位账号在本部门子树的完整自助动线：六类创建（T01/M-A3）、编辑
自己与总管理员代建页（T02/M-A4）、发布/下线（T03/M-A5、M-A6、N13）、
到期自动归档（T04/M-A7、N13）。全程 Django test Client 走真实后台
HTTP 动线；正向断言附带修订/日志留痕（PRD §5）。
"""

import datetime as dt

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from notices.models import NoticePage
from wagtail.models import Page, PageLogEntry

from .helpers import future
from .permission_helpers import (
    article_form,
    build_permission_world,
    guide_form,
    login_client,
    material_form,
    notice_form,
    rev_count,
    search_hit,
    software_form,
)


class T01CreateSixContentTypesTests(TestCase):
    """T01 · 正向 · 部门账号在本部门各容器创建六类内容页（M-A3；N13 草稿不可见）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_create_six_content_types(self):
        w = self.world
        client = login_client(w["user_a"])
        dept_id = w["dept_a"].id
        cases = [
            ("chronicle", "notices", "noticepage", notice_form("A部门通知", "a-notice", dept_id)),
            (
                "events",
                "notices",
                "noticepage",
                notice_form("A部门活动通知", "a-event-notice", dept_id, event=True),
            ),
            (
                "chronicle",
                "notices",
                "articlepage",
                article_form("A部门文章", "a-article", dept_id),
            ),
            (
                "materials",
                "resources",
                "materialpage",
                material_form(
                    "A部门资料", "a-material", dept_id, w["discipline"].id, w["material_type"].id
                ),
            ),
            (
                "software",
                "resources",
                "softwaretoolpage",
                software_form("A部门工具", "a-software", dept_id, [w["platform"].id]),
            ),
            (
                "guide",
                "guides",
                "guidepage",
                guide_form("A部门指南", "a-guide", dept_id, w["guide_category"].id),
            ),
        ]
        anon = Client()
        for section_slug, app_label, model, data in cases:
            with self.subTest(page_type=model):
                container = w["a_containers"][section_slug]
                resp = client.post(
                    reverse("wagtailadmin_pages:add", args=[app_label, model, container.pk]),
                    data,
                )
                page = Page.objects.filter(slug=data["slug"]).first()
                self.assertIsNotNone(page, f"{model} 创建失败 HTTP {resp.status_code}")
                self.assertFalse(page.live, "保存草稿语义")
                self.assertEqual(page.owner_id, w["user_a"].id, "账号成为 owner（M-A3）")
                self.assertEqual(rev_count(page.pk), 1, "修订历史留痕（PRD §5）")
                revision = page.revisions.order_by("-pk").first()
                self.assertEqual(revision.user_id, w["user_a"].id)
                self.assertIsNotNone(revision.created_at)
                # 草稿不出现在前台与默认搜索（N13）
                self.assertEqual(anon.get(page.url).status_code, 404)
                self.assertFalse(search_hit(anon, data["title"], data["slug"]))


class T02EditOwnAndAdminCreatedTests(TestCase):
    """T02 · 正向 · 编辑自己页面与总管理员代建页（M-A4：edit 覆盖子树内任意归属）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()
        # 总管理员在 A 容器下代建一页（owner=总管理员，草稿）
        w = cls.world
        cls.admin_page = NoticePage(
            title="总管理员代建通知",
            slug="a-admin-notice",
            owner=w["admin"],
            department=w["dept_a"],
            summary="代建摘要",
            expire_at=future(days=365),
        )
        w["a_containers"]["chronicle"].add_child(instance=cls.admin_page)
        cls.admin_page.live = False
        cls.admin_page.save_revision(user=w["admin"])

    def test_edit_own_page(self):
        w = self.world
        client = login_client(w["user_a"])
        own = NoticePage(
            title="A新建通知",
            slug="a-own-notice",
            owner=w["user_a"],
            department=w["dept_a"],
            summary="原摘要",
            expire_at=future(days=365),
        )
        w["a_containers"]["chronicle"].add_child(instance=own)
        own.live = False
        own.save_revision(user=w["user_a"])
        before = rev_count(own.pk)
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[own.pk]),
            notice_form(
                "A新建通知（改）",
                "a-own-notice",
                w["dept_a"].id,
                summary="改后摘要",
                tags=[w["tag"].id],  # 受控标签选用（M-D3 注：属编辑面）
            ),
        )
        self.assertEqual(rev_count(own.pk), before + 1, f"HTTP {resp.status_code}")
        latest = own.revisions.order_by("-pk").first()
        self.assertEqual(latest.user_id, w["user_a"].id, "修订记录操作者（PRD §5）")

    def test_edit_admin_created_page_in_own_subtree(self):
        w = self.world
        client = login_client(w["user_a"])
        before = rev_count(self.admin_page.pk)
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[self.admin_page.pk]),
            notice_form(
                "总管理员代建通知（部门改）",
                "a-admin-notice",
                w["dept_a"].id,
                summary="部门账号代改",
            ),
        )
        self.assertEqual(rev_count(self.admin_page.pk), before + 1, f"HTTP {resp.status_code}")
        self.admin_page.refresh_from_db()
        self.assertEqual(self.admin_page.owner_id, w["admin"].id, "owner 不被改写")


class T03PublishUnpublishTests(TestCase):
    """T03 · 正向 · 发布与下线（M-A5 无审批；M-A6；N13 四态联动）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def _make_draft(self):
        w = self.world
        page = NoticePage(
            title="A待发布通知",
            slug="a-pub-notice",
            owner=w["user_a"],
            department=w["dept_a"],
            summary="发布摘要",
            expire_at=future(days=365),
        )
        w["a_containers"]["chronicle"].add_child(instance=page)
        page.live = False
        page.save_revision(user=w["user_a"])
        return page

    def _publish_flow(self):
        """发布动线（T03①②）＋断言；返回已发布页面供下线用例复用。"""
        w = self.world
        page = self._make_draft()
        client = login_client(w["user_a"])
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[page.pk]),
            {
                **notice_form("A待发布通知", "a-pub-notice", w["dept_a"].id),
                "action-publish": "action-publish",
            },
        )
        page.refresh_from_db()
        self.assertTrue(page.live, f"发布成功 HTTP {resp.status_code}（无审批，M-A5）")
        self.assertTrue(
            PageLogEntry.objects.filter(
                page_id=page.pk, action="wagtail.publish", user=w["user_a"]
            ).exists(),
            "发布动作留痕（操作者/时间，PRD §5）",
        )
        anon = Client()
        self.assertEqual(anon.get(page.url).status_code, 200, "发布后前台可见")
        self.assertTrue(search_hit(anon, "A待发布通知", "a-pub-notice"), "默认搜索命中")
        return page

    def test_publish_without_approval(self):
        self._publish_flow()

    def test_unpublish_retains_content(self):
        page = self._publish_flow()
        w = self.world
        client = login_client(w["user_a"])
        revisions_before = rev_count(page.pk)
        resp = client.post(reverse("wagtailadmin_pages:unpublish", args=[page.pk]), {})
        page.refresh_from_db()
        self.assertFalse(page.live, f"下线成功 HTTP {resp.status_code}（M-A6）")
        self.assertTrue(Page.objects.filter(pk=page.pk).exists(), "页面保留在库")
        self.assertEqual(rev_count(page.pk), revisions_before, "修订保留")
        anon = Client()
        self.assertEqual(anon.get(page.url).status_code, 404, "下线后前台 404（N13）")
        self.assertFalse(search_hit(anon, "A待发布通知", "a-pub-notice"), "默认搜索不再出现（N13）")


class T04ExpiryArchiveTests(TestCase):
    """T04 · 正向 · 通知到期自动归档（M-A7；N13；PRD §23 场景 2）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_expired_notice_exits_frontend_keeps_content(self):
        w = self.world
        page = NoticePage(
            title="A到期活动通知",
            slug="a-exp-notice",
            owner=w["user_a"],
            department=w["dept_a"],
            summary="到期摘要",
            expire_at=future(days=365),
            # events 板块口径（§7.2）：活动通知须带活动字段
            event_start_at=timezone.now() + dt.timedelta(days=30),
            event_end_at=timezone.now() + dt.timedelta(days=30, hours=8),
            event_location="测试活动地点",
        )
        w["a_containers"]["events"].add_child(instance=page)
        page.live = False
        page.save_revision(user=w["user_a"]).publish(user=w["user_a"])
        page.refresh_from_db()
        self.assertTrue(page.live, "前置：已发布")

        revisions_before = rev_count(page.pk)
        # 场景操纵（时间快进）：模拟到期时刻到达（M4.3 同口径）
        Page.objects.filter(pk=page.pk).update(expire_at=timezone.now() - dt.timedelta(minutes=1))
        call_command("publish_scheduled")
        page.refresh_from_db()
        self.assertFalse(page.live, "到期自动下线（M-A7）")
        self.assertTrue(page.expired, "expired 标记置位")
        anon = Client()
        # M5.2 §7.2 登记差异：expired 具名 URL 放行渲染（载体①）＋搜索纳入
        # （ARCHIVE-SEARCH）；默认列表退出断言见 test_current_default.py。
        self.assertEqual(anon.get(page.url).status_code, 200, "expired URL 放行（M5.2 载体①）")
        self.assertTrue(search_hit(anon, "A到期活动通知", "a-exp-notice"), "搜索命中（M5.2）")
        self.assertEqual(rev_count(page.pk), revisions_before, "内容与修订保留在库")
        # 部门账号后台仍可见（M-A1）
        client = login_client(w["user_a"])
        self.assertEqual(
            client.get(
                reverse("wagtailadmin_explore", args=[w["a_containers"]["events"].pk])
            ).status_code,
            200,
            "部门账号后台仍可查看（M-A1）",
        )
