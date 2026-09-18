"""E9 预览链路端到端（ADR-0008 §3.1 五步流）：后台铸造 → /preview/ 承接
→ /api/v1/preview 兑换。

铸造面挂 wagtailadmin（require_admin_access）＋与后台预览同一 can_edit
要求；票据绑定（会话、用户、页面 pk）、60s 有效期；兑换零写入（无新
修订、无页面变更、FormState 原样），兑换请求无需编辑器 Cookie（Astro
SSR 服务器到服务器同构）。
"""

from urllib.parse import parse_qs, urlencode, urlparse

from api.views import PREVIEW_TOKEN_SALT
from django.contrib.auth import get_user_model
from django.core import signing
from django.test import Client, TestCase
from django.utils import timezone
from wagtail.admin.models import FormState

from .helpers import (
    build_sections,
    make_container,
    make_department,
    make_notice,
    notice_data,
)


class PreviewFlowTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("预览测试处", "prev-dept")
        cls.container = make_container(cls.sections["chronicle"], cls.department)
        cls.notice = make_notice(cls.container, slug="prev-notice", title="预览通知", publish=True)
        cls.editor = get_user_model().objects.create_superuser(
            "prev-editor", "prev@example.com", "prev-editor-pass-123"
        )

    def setUp(self):
        self.admin_client = Client()
        self.admin_client.force_login(self.editor)

    def _form_state(self, title):
        """编辑器草稿暂存（后台 PreviewOnEdit 存草稿同一写入位）。"""
        obj = self.notice.get_latest_revision_as_object()
        data = urlencode(notice_data(self.container, title=title))
        state, _ = FormState.objects.update_or_create_by_instance(
            obj,
            parent_object_id="",
            user=self.editor,
            defaults={"data": data, "last_updated_at": timezone.now()},
        )
        return state

    def _mint_token(self):
        response = self.admin_client.get(f"/admin/headless-preview/{self.notice.pk}/")
        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertTrue(location.startswith("/preview/?token="), location)
        token = parse_qs(urlparse(location).query)["token"][0]
        return token


class MintEndpointTests(PreviewFlowTestCase):
    def test_mint_binds_session_user_page(self):
        """铸造票据载荷绑定（当前管理会话、用户、页面）；60s 有效期。"""
        token = self._mint_token()
        payload = signing.loads(token, salt=PREVIEW_TOKEN_SALT, max_age=60)
        self.assertEqual(payload["u"], self.editor.pk)
        self.assertEqual(payload["p"], self.notice.pk)
        self.assertEqual(payload["s"], self.admin_client.session.session_key)

    def test_mint_anonymous_redirects_to_admin_login(self):
        """匿名＝管理面登录门（require_admin_access），不泄露页面存在性。"""
        response = Client().get(f"/admin/headless-preview/{self.notice.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_mint_rejects_non_content_page(self):
        """非五类内容页（结构页）→ 404，不铸造。"""
        root_pk = self.notice.get_parent().get_parent().pk  # SectionPage 非内容页
        response = self.admin_client.get(f"/admin/headless-preview/{root_pk}/")
        self.assertEqual(response.status_code, 404)

    def test_mint_rejects_user_without_change_permission(self):
        """有后台访问权但无该页编辑权 → 404（与后台预览同一 can_edit）。"""
        from django.contrib.auth.models import Group, Permission

        group = Group.objects.create(name="预览仅后台")
        group.permissions.add(
            Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin")
        )
        visitor = get_user_model().objects.create_user(
            "prev-visitor", "visitor@example.com", "prev-visitor-pass-123"
        )
        visitor.groups.add(group)
        gated = Client()
        gated.force_login(visitor)
        response = gated.get(f"/admin/headless-preview/{self.notice.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_edit_view_shows_preview_exit_button(self):
        """编辑页头按钮（register_page_header_buttons）：文案＋铸造 URL。"""
        response = self.admin_client.get(f"/admin/pages/{self.notice.pk}/edit/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("新前端预览", body)
        self.assertIn(f"/admin/headless-preview/{self.notice.pk}/", body)


class RedemptionTests(PreviewFlowTestCase):
    def test_redemption_happy_path(self):
        """五步流全通：草稿暂存 → 铸造 → 兑换（无编辑器 Cookie）→
        E6 同构数据＋preview:true＋草稿标题。"""
        self._form_state("预览新标题")
        token = self._mint_token()
        # Astro SSR 服务器到服务器：全新客户端零 Cookie 兑换。
        server = Client()
        self.assertFalse(server.cookies)
        response = server.get("/api/v1/preview", {"token": token})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["preview"])
        self.assertEqual(data["title"], "预览新标题")
        self.assertEqual(data["type"], "notice")
        # E6 同构：正式详情仍为已发布标题（草稿不出公开面）。
        published = self.client.get(f"/api/v1/pages/{self.notice.url.strip('/')}").json()
        self.assertEqual(published["title"], "预览通知")
        self.assertNotIn("preview", published)

    def test_redemption_zero_write(self):
        """兑换零写入：无新修订、页面行不变、FormState 原样。"""
        from wagtail.models import Page, Revision

        form_state = self._form_state("零写入草稿标题")
        token = self._mint_token()

        def snapshot():
            page = Page.objects.get(pk=self.notice.pk)
            return {
                "revisions": Revision.objects.filter(object_id=self.notice.pk).count(),
                "title": page.title,
                "live": page.live,
                "formstate_count": FormState.objects.count(),
                "formstate_data": FormState.objects.get(pk=form_state.pk).data,
            }

        before = snapshot()
        response = Client().get("/api/v1/preview", {"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(snapshot(), before)

    def test_redemption_requires_matching_formstate_user(self):
        """FormState 用户与票据用户不一致 → 404（兑换按载荷用户取暂存）。"""
        self._form_state("他人草稿标题")
        colleague = get_user_model().objects.create_superuser(
            "prev-colleague", "colleague@example.com", "prev-colleague-pass-123"
        )
        self.admin_client.force_login(colleague)
        token = self._mint_token()
        response = Client().get("/api/v1/preview", {"token": token})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_redemption_data_is_preview_form_path_rebuild(self):
        """草稿数据取自表单暂存（同后台预览表单路径），非最新修订。"""
        obj = self.notice.get_latest_revision_as_object()
        data = urlencode(notice_data(self.container, title="表单路径草稿", summary="表单路径摘要"))
        FormState.objects.update_or_create_by_instance(
            obj,
            parent_object_id="",
            user=self.editor,
            defaults={"data": data, "last_updated_at": timezone.now()},
        )[0]
        token = self._mint_token()
        payload = Client().get("/api/v1/preview", {"token": token}).json()
        self.assertEqual(payload["title"], "表单路径草稿")
        self.assertEqual(payload["summary"], "表单路径摘要")
        self.assertEqual(payload["department"], {"name": "预览测试处", "slug": "prev-dept"})
        self.assertIsNone(payload["event"])
