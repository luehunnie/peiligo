"""T14–T16 总管理员工厂面与前台/后台/角色边界（M4.3 t16 迁移；矩阵 §6）。

T14 总管理员（纯组权限行权，非 superuser）工厂面正向全链（§4 账号生命
周期、词表/容器/推荐位/站点设置/部门子树代建）；T15 跨部门治理与永久
删除的守卫放行面（M-B4/B5/A8 R1 列——守卫只拒绝不放行的另一侧直证）；
T16 前台四态可见性（N13）、容器 URL 404（ADR-0004 决策 2）、sitemap/
导航（N14）、后台入口边界与 R3 型账号（N09/N10）。用户/组治理 DB 级
审计已由 F-08B（R-05 方案 B）经 Wagtail ModelLogEntry 落地——原
「无 DB 级留痕」断言按 requirement-approved behavior change 更新为
正向断言（Human 批准 2026-09-01）。
"""

import datetime as dt
import io

from departments.models import Department, DepartmentContainerPage
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from guides.models import GuideCategory
from home.models import FeaturedItem
from notices.models import ArticlePage, NoticePage
from resources.models import Discipline, MaterialType, Platform, SoftwareToolPage
from wagtail.models import ModelLogEntry, Page, Revision

from .helpers import future
from .permission_helpers import (
    PASSWORD,
    build_permission_world,
    bulk_delete_url,
    login_client,
    notice_form,
    rev_count,
    search_hit,
    software_form,
)


class T14AdminFactoryTests(TestCase):
    """T14 · 正向 · 总管理员工厂面（is_superuser=False，纯组权限行权）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_admin_home_reachable_as_group_member(self):
        w = self.world
        client = login_client(w["admin"])
        resp = client.get(reverse("wagtailadmin_home"))
        self.assertEqual(resp.status_code, 200, "纯组权限即可行权后台")
        self.assertFalse(w["admin"].is_superuser)

    def test_dept_account_lifecycle(self):
        """① 创建 → 停用 → 重置口令复启（§4 生命周期）。"""
        w = self.world
        client = login_client(w["admin"])
        resp = client.post(
            reverse("wagtailusers_users:add"),
            {
                "username": "t44-dept-c",
                "email": "c@t44.example.com",
                "first_name": "部门C",
                "last_name": "岗位",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        user_c = get_user_model().objects.filter(username="t44-dept-c").first()
        self.assertIsNotNone(user_c, f"创建部门岗位账号 HTTP {resp.status_code}")
        # F-08B（R-05 方案 B，Human 2026-09-01 批准的 requirement-approved
        # behavior change）：用户治理操作必须落 DB 级审计——Wagtail 官方
        # ModelLogEntry（django.contrib.admin 的 LogEntry 仍不启用）。
        self.assertEqual(
            LogEntry.objects.filter(object_id=str(user_c.pk)).count(),
            0,
            "记录性核查：django.contrib.admin LogEntry 仍非本项目审计载体",
        )
        self.assertTrue(
            ModelLogEntry.objects.filter(
                content_type__app_label="auth",
                content_type__model="user",
                object_id=str(user_c.pk),
                action="wagtail.create",
                user_id=w["admin"].pk,
            ).exists(),
            "R-05：后台建用户必须留 DB 审计（actor=操作管理员）",
        )
        resp = client.post(
            reverse("wagtailusers_users:edit", args=[user_c.pk]),
            {
                "username": "t44-dept-c",
                "email": "c@t44.example.com",
                "first_name": "部门C",
                "last_name": "岗位",
                "password1": "",
                "password2": "",
            },  # 不勾 is_active＝停用（表单字段缺省 False）
        )
        user_c.refresh_from_db()
        self.assertFalse(user_c.is_active, f"停用 HTTP {resp.status_code}")
        resp = client.post(
            reverse("wagtailusers_users:edit", args=[user_c.pk]),
            {
                "username": "t44-dept-c",
                "email": "c@t44.example.com",
                "first_name": "部门C",
                "last_name": "岗位",
                "is_active": "on",
                "password1": "t44-reset-pass-67890",
                "password2": "t44-reset-pass-67890",
            },
        )
        fresh = Client()
        self.assertTrue(
            fresh.login(username="t44-dept-c", password="t44-reset-pass-67890"),
            f"重置口令后新凭据可登录 HTTP {resp.status_code}",
        )

    def test_create_department_and_container(self):
        """② 新建 Department 词表项＋板块下建对应容器（M-C2）。"""
        w = self.world
        client = login_client(w["admin"])
        resp = client.post(
            reverse("wagtailsnippets_departments_department:add"),
            {"name": "边界部门C", "slug": "t44-dept-c", "sort_order": "9", "is_active": "on"},
        )
        dept_c = Department.objects.filter(slug="t44-dept-c").first()
        self.assertIsNotNone(dept_c, f"新建 Department HTTP {resp.status_code}")
        resp = client.post(
            reverse(
                "wagtailadmin_pages:add",
                args=["departments", "departmentcontainerpage", w["sections"]["materials"].pk],
            ),
            {"title": "边界容器·部门C", "slug": "", "department": str(dept_c.pk)},
        )
        cont_c = DepartmentContainerPage.objects.filter(department=dept_c).first()
        self.assertIsNotNone(cont_c, f"板块下建容器 HTTP {resp.status_code}（M-C2）")

    def test_manage_content_vocabularies(self):
        """③ 管理四个内容词表各一条（M-D2）。"""
        w = self.world
        client = login_client(w["admin"])
        cases = [
            ("resources_discipline", {"name": "边界学科", "sort_order": "5"}, Discipline),
            ("resources_materialtype", {"name": "边界资料类型", "sort_order": "5"}, MaterialType),
            ("resources_platform", {"name": "边界平台", "sort_order": "5"}, Platform),
            ("guides_guidecategory", {"name": "边界指南类别", "sort_order": "5"}, GuideCategory),
        ]
        for url_model, data, model in cases:
            with self.subTest(vocab=model.__name__):
                resp = client.post(reverse(f"wagtailsnippets_{url_model}:add"), data)
                self.assertTrue(
                    model.objects.filter(name=data["name"]).exists(),
                    f"新增{model.__name__} HTTP {resp.status_code}（M-D2）",
                )

    def test_create_featured_item(self):
        """④ 建 FeaturedItem（指向/起止窗口/启用；M-D4/N06 正向侧，PRD §9）。"""
        w = self.world
        client = login_client(w["admin"])
        resp = client.post(
            reverse("wagtailsnippets_home_featureditem:add"),
            {
                "content": str(w["page_b_live"].pk),
                "start_at": "2026-09-01 09:00",
                "end_at": "2026-10-01 09:00",
                "enabled": "on",
            },
        )
        fi = FeaturedItem.objects.filter(content=w["page_b_live"]).first()
        self.assertIsNotNone(fi, f"新建 FeaturedItem HTTP {resp.status_code}")
        self.assertTrue(fi.enabled)
        # 墙钟钟面断言（M5.1 §4.4②）：读回值经 localtime 按当前时区（Asia/Shanghai）
        # 渲染钟面——表单提交钟面→DB aware UTC→localtime 读回往返一致，消除对
        # TIME_ZONE 取值的隐式依赖（裸 strftime 渲染 UTC 钟面，切时区后必红）。
        self.assertEqual(
            timezone.localtime(fi.start_at).strftime("%Y-%m-%d %H:%M"), "2026-09-01 09:00"
        )
        self.assertEqual(
            timezone.localtime(fi.end_at).strftime("%Y-%m-%d %H:%M"), "2026-10-01 09:00"
        )

    def test_edit_site_settings(self):
        """⑤ 改 SiteSettings 紧急提示与反馈邮箱（M-E1 正向侧）。"""
        w = self.world
        client = login_client(w["admin"])
        resp = client.post(
            reverse("wagtailsettings:edit", args=["home", "sitesettings", w["site"].pk]),
            {
                "alert_text": "边界测试紧急提示",
                "alert_start_at": "",
                "alert_end_at": "",
                "feedback_email": "t44@example.com",
                "redirect_notice_text": "",
            },
        )
        w["site_settings"].refresh_from_db()
        self.assertEqual(
            w["site_settings"].alert_text, "边界测试紧急提示", f"HTTP {resp.status_code}"
        )
        self.assertEqual(w["site_settings"].feedback_email, "t44@example.com")

    def test_proxy_create_and_edit_in_dept_subtree(self):
        """⑥ 在部门 A 子树代建页并编辑（M-A3/A4 R1 列）。"""
        w = self.world
        client = login_client(w["admin"])
        resp = client.post(
            reverse(
                "wagtailadmin_pages:add",
                args=["notices", "noticepage", w["a_containers"]["chronicle"].pk],
            ),
            notice_form("总管理员代建边界通知", "t44-admin-bnd", w["dept_a"].id),
        )
        page = Page.objects.filter(slug="t44-admin-bnd").first()
        self.assertIsNotNone(page, f"代建 HTTP {resp.status_code}")
        self.assertEqual(page.owner_id, w["admin"].id, "owner=总管理员")
        before = rev_count(page.pk)
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[page.pk]),
            notice_form(
                "总管理员代建边界通知（改）",
                "t44-admin-bnd",
                w["dept_a"].id,
                summary="管理员编辑代建页",
            ),
        )
        self.assertEqual(rev_count(page.pk), before + 1, f"编辑 HTTP {resp.status_code}")


class T15AdminGovernanceTests(TestCase):
    """T15 · 正向 · 总管理员跨部门治理与永久删除（守卫放行面）。"""

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def _mk_b_page(self, title, slug):
        """B 子树待删素材（owner=B，草稿）。"""
        w = self.world
        page = NoticePage(
            title=title,
            slug=slug,
            owner=w["user_b"],
            department=w["dept_b"],
            summary="B 页摘要",
            expire_at=future(days=365),
        )
        page.live = False
        w["b_chron"].add_child(instance=page)
        page.save_revision(user=w["user_b"])
        return page

    def test_cross_dept_edit_then_unpublish(self):
        """① 跨部门纠错（M-B4 R1）＋② 下线（M-B5/B6 R1）。"""
        w = self.world
        client = login_client(w["admin"])
        page_b = w["page_b_live"]
        before = rev_count(page_b.pk)
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[page_b.pk]),
            notice_form(
                "B部门已发布通知（管理员纠错）",
                "t44-b-live",
                w["dept_b"].id,
                summary="管理员跨部门纠错",
            ),
        )
        page_b.refresh_from_db()
        self.assertGreater(
            rev_count(page_b.pk), before, f"跨部门编辑 HTTP {resp.status_code}（M-B4）"
        )
        self.assertTrue(page_b.live)

        resp = client.post(reverse("wagtailadmin_pages:unpublish", args=[page_b.pk]), {})
        page_b.refresh_from_db()
        self.assertFalse(page_b.live, f"下线 HTTP {resp.status_code}")
        revisions_before = rev_count(page_b.pk)
        anon = Client()
        self.assertEqual(anon.get(page_b.url).status_code, 404, "下线后前台 404")
        self.assertTrue(Page.objects.filter(pk=page_b.pk).exists(), "页面保留在库")
        self.assertEqual(rev_count(page_b.pk), revisions_before, "修订保留")

    def test_single_delete_passes_guard(self):
        """③ 单条路径永久删除：页面与修订一并移出库（M-A8/B7 R1）。"""
        w = self.world
        client = login_client(w["admin"])
        target = self._mk_b_page("B待删页一", "t44-b-del-1")
        resp = client.post(reverse("wagtailadmin_pages:delete", args=[target.pk]), {})
        self.assertFalse(
            Page.objects.filter(pk=target.pk).exists(), f"HTTP {resp.status_code}（守卫放行）"
        )
        self.assertFalse(Revision.objects.filter(object_id=target.pk).exists(), "修订一并删除")

    def test_bulk_delete_passes_guard(self):
        """③ 批量路径放行（镜像 T08 双路径的守卫另一侧）。"""
        w = self.world
        client = login_client(w["admin"])
        ids = [self._mk_b_page(f"B批量待删{i}", f"t44-b-del-b{i}").pk for i in (1, 2)]
        resp = client.post(bulk_delete_url(*ids), {})
        self.assertEqual(
            Page.objects.filter(pk__in=ids).count(), 0, f"HTTP {resp.status_code}（管理员整批放行）"
        )


class T16BoundaryTests(TestCase):
    """T16 · 边界 · 前台四态/容器 URL/sitemap/后台入口/角色边界。"""

    @classmethod
    def setUpTestData(cls):
        w = cls.world = build_permission_world()

        # 四态素材（M-A2/B2/C1）：live 文章、draft 软件、unpublished 通知、expired 活动通知
        article = ArticlePage(
            title="A边界文章",
            slug="t44-bnd-article",
            owner=w["user_a"],
            department=w["dept_a"],
            summary="边界文章摘要",
        )
        article.live = False
        w["a_containers"]["chronicle"].add_child(instance=article)
        article.save_revision(user=w["user_a"]).publish(user=w["user_a"])

        # draft 软件页走真实创建动线（platforms m2m 校验在保存时点，ORM 无法
        # 先建后挂——HTTP 表单流同 t16 口径）
        login_client(w["user_a"]).post(
            reverse(
                "wagtailadmin_pages:add",
                args=["resources", "softwaretoolpage", w["a_containers"]["software"].pk],
            ),
            software_form("A边界软件", "t44-bnd-software", w["dept_a"].id, [w["platform"].id]),
        )

        unpub = NoticePage(
            title="A边界下线通知",
            slug="t44-bnd-notice",
            owner=w["user_a"],
            department=w["dept_a"],
            summary="下线摘要",
            expire_at=future(days=365),
        )
        unpub.live = False
        w["a_containers"]["chronicle"].add_child(instance=unpub)
        unpub.save_revision(user=w["user_a"]).publish(user=w["user_a"])
        # 下线走真实后台动线（同 T03 口径；ORM 直调 action 会触发与视图不同的
        # 权限检查路径）
        login_client(w["user_a"]).post(reverse("wagtailadmin_pages:unpublish", args=[unpub.pk]), {})

        expired = NoticePage(
            title="A边界到期活动通知",
            slug="t44-bnd-event",
            owner=w["user_a"],
            department=w["dept_a"],
            summary="到期摘要",
            expire_at=future(days=365),
            event_start_at=timezone.now() + dt.timedelta(days=30),
            event_end_at=timezone.now() + dt.timedelta(days=30, hours=8),
            event_location="测试活动地点",
        )
        expired.live = False
        w["a_containers"]["events"].add_child(instance=expired)
        expired.save_revision(user=w["user_a"]).publish(user=w["user_a"])
        Page.objects.filter(pk=expired.pk).update(
            expire_at=timezone.now() - dt.timedelta(minutes=1)
        )
        call_command("publish_scheduled", stdout=io.StringIO())

        cls.states = {
            "live": ArticlePage.objects.get(slug="t44-bnd-article"),
            "draft": SoftwareToolPage.objects.get(slug="t44-bnd-software"),
            "unpublished": NoticePage.objects.get(slug="t44-bnd-notice"),
            "expired": NoticePage.objects.get(slug="t44-bnd-event"),
        }

    def test_frontend_four_states(self):
        """① 已发布内容前台可见；草稿/下线 404（N13）。M5.2 §7.2 登记差异：
        expired 具名 URL 由 404 改放行渲染（载体①）——带「已过期」横幅。"""
        anon = Client()
        codes = {k: anon.get(p.url).status_code for k, p in self.states.items()}
        self.assertEqual(codes["live"], 200, f"实测：{codes}")
        for key in ("draft", "unpublished"):
            self.assertEqual(codes[key], 404, f"{key} 前台 404（N13）；实测：{codes}")
        response = anon.get(self.states["expired"].url)
        self.assertEqual(response.status_code, 200, "expired 载体①放行（M5.2）")
        self.assertContains(response, "已过期")

    def test_search_only_live(self):
        """① 搜索：已发布命中；草稿/下线不出现（N13）。M5.2 §7.2 登记差异：
        /search/ 升级 ARCHIVE-SEARCH——expired 默认命中（PA-33）。"""
        anon = Client()
        live = self.states["live"]
        self.assertTrue(search_hit(anon, live.title, live.slug))
        for key in ("draft", "unpublished"):
            page = self.states[key]
            self.assertFalse(search_hit(anon, page.title, page.slug), f"{key} 不入搜索（N13）")
        expired = self.states["expired"]
        self.assertTrue(search_hit(anon, expired.title, expired.slug), "expired 入搜索（M5.2）")

    def test_container_url_404(self):
        """② 未登录直达容器 URL → 404（ADR-0004 决策 2）。"""
        anon = Client()
        w = self.world
        self.assertEqual(anon.get(w["b_chron"].url).status_code, 404, f"GET {w['b_chron'].url}")

    def test_containers_not_in_sitemap_or_nav(self):
        """③ 容器不入 sitemap/前台导航，板块页在（N14）。"""
        anon = Client()
        w = self.world
        sitemap = anon.get("/sitemap.xml").content.decode()
        self.assertNotIn(f"{w['b_chron'].url}</loc>", sitemap, "B 容器不入 sitemap（N14）")
        self.assertNotIn(
            f"{w['a_containers']['chronicle'].url}</loc>", sitemap, "A 容器不入 sitemap（N14）"
        )
        self.assertIn("/chronicle/</loc>", sitemap, "板块页在 sitemap")
        home_html = anon.get("/").content.decode()
        # F-04 起首页内容卡（最新通知等数据区）合法携带以容器路径为前缀的
        # 内容页 URL，全页子串断言过宽；收窄为「容器不可作为链接目标」
        # （恰等 href）——语义仍覆盖前台导航与一切数据区。
        self.assertNotIn(f'href="{w["b_chron"].url}"', home_html, "容器不入前台导航（N14）")
        self.assertNotIn(
            f'href="{w["a_containers"]["chronicle"].url}"',
            home_html,
            "容器不入前台导航（N14）",
        )

    def test_anonymous_admin_boundaries(self):
        """④ 未登录访问 /admin/ 重定向登录页；错误凭据不泄露账号存在性。"""
        anon = Client()
        resp = anon.get("/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])
        resp = anon.post("/admin/login/", {"username": "nobody-t44", "password": "wrong-pass-123"})
        self.assertEqual(resp.status_code, 200, "错误凭据重渲染登录页（统一失败页）")

    def test_r3_account_no_admin_access(self):
        """⑤ R3 型账号（零组零权限）不可达后台（N09）；superuser 规约在场（M-G5/N10）。"""
        get_user_model().objects.create_user("t44-plain", password=PASSWORD)
        client = Client()
        self.assertTrue(client.login(username="t44-plain", password=PASSWORD))
        resp = client.get("/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"], "无 access_admin 即不可达后台（N09）")
        self.assertEqual(
            get_user_model().objects.filter(is_superuser=True).count(),
            0,
            "superuser 规约：全程零 superuser 账号（N10；break-glass 仅故障恢复留痕用）",
        )

    def test_dept_account_admin_home(self):
        """⑥ 已登录部门账号后台首页 200（可见≠可操作——操作面以 T05–T13 拒绝断言为准）。"""
        w = self.world
        client = login_client(w["user_a"])
        self.assertEqual(client.get(reverse("wagtailadmin_home")).status_code, 200)

    def test_browser_tree_api_reachable(self):
        """⑥ 浏览器树 API 可达（OQ-2 记录：可见性≠操作权，越权面由拒绝断言守）。

        Wagtail 7.4.3（PYSEC-2026-3939 修复）将 listing 查询集收窄为
        explorable_instances(user)：可达性探针改取部门 A 自己的容器；
        越界父节点（root）如今按设计返回 400，一并断言为回归守卫。
        """
        w = self.world
        client = login_client(w["user_a"])
        resp = client.get(
            "/admin/api/main/pages/", {"child_of": w["a_containers"]["chronicle"].id}
        )
        self.assertEqual(resp.status_code, 200)
        root_id = Page.get_first_root_node().id
        resp = client.get("/admin/api/main/pages/", {"child_of": root_id})
        self.assertEqual(resp.status_code, 400)
