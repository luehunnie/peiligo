"""API v1 安全/权限语义（ADR-0008 S 条款）。

S7 无 CORS（Compose 内网同源）、草稿内容不出公开响应、E9 反预言机
（一切失败 uniform 404，不泄露失败原因）、E7 恒不 4xx、CSP 盖章与
no-store 全响应——锁定 API 面不新增攻击面。
"""

from api.views import PREVIEW_TOKEN_SALT
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase
from django.utils.module_loading import import_module
from search.services import SEARCHABLE_PAGE_MODELS
from wagtail.models import Site

from .helpers import build_sections, make_container, make_department, make_notice

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


def _mint(session_key, user_pk, page_pk, salt=PREVIEW_TOKEN_SALT):
    return signing.dumps({"s": session_key, "u": user_pk, "p": page_pk}, salt=salt)


class SecurityDataTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("安全测试处", "sec-dept")
        cls.container = make_container(cls.sections["chronicle"], cls.department)
        cls.notice = make_notice(cls.container, slug="sec-notice", title="安全通知", publish=True)
        cls.editor = get_user_model().objects.create_superuser(
            "sec-editor", "sec@example.com", "sec-editor-pass-123"
        )


class ApiSurfaceSecurityTests(SecurityDataTestCase):
    def test_unknown_api_path_json_envelope_any_method(self):
        """/api/v1/ 空间未匹配路径（含尾斜杠形态、任意方法）＝JSON 404
        封装，不落 wagtail HTML 404。"""
        for path, method in (
            ("/api/v1/nonexistent", "get"),
            ("/api/v1/chrome/", "get"),  # 尾斜杠≠契约路径
            ("/api/v1/sections", "get"),
            ("/api/v1/bogus", "post"),
        ):
            with self.subTest(path=path, method=method):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_no_cors_headers_anywhere(self):
        """S7：无 CORS——任何响应（含 404/405）不带 Access-Control-*。"""
        responses = [
            self.client.get("/api/v1/chrome"),
            self.client.get("/api/v1/pages/chronicle/sec-dept/missing"),
            self.client.post("/api/v1/chrome"),
        ]
        for response in responses:
            for header in response.headers.items():
                self.assertFalse(
                    header[0].lower().startswith("access-control-"),
                    f"意外 CORS 头：{header}",
                )

    def test_draft_content_never_in_public_responses(self):
        """草稿标题不出现在任何 E1–E8 响应（含错误文案）。"""
        make_notice(self.container, slug="leak-draft", title="机密草稿绝密标题")
        endpoints = [
            "/api/v1/chrome",
            "/api/v1/home",
            "/api/v1/sections/chronicle",
            "/api/v1/sections/chronicle/archive",
            "/api/v1/search?q=机密",
            "/api/v1/sitemap",
            "/api/v1/pages/chronicle/sec-dept/leak-draft",
        ]
        for path in endpoints:
            response = self.client.get(path)
            with self.subTest(path=path):
                self.assertNotIn("机密草稿绝密标题", response.content.decode())

    def test_csp_stamped_on_api_responses(self):
        """/api/ 非管理面前缀——公开 CSP 照章盖章。"""
        response = self.client.get("/api/v1/chrome")
        self.assertIn("Content-Security-Policy", response.headers)

    def test_no_store_on_all_responses(self):
        """F1：no-store 全响应（200/404/405 一律）。"""
        for response in (
            self.client.get("/api/v1/chrome"),
            self.client.get("/api/v1/pages/chronicle/sec-dept/missing"),
            self.client.post("/api/v1/chrome"),
        ):
            self.assertEqual(response["Cache-Control"], "no-store")

    def test_e7_hostile_inputs_never_4xx(self):
        """E7 恒 200（拒绝态 ok:false＋problem），敌意输入不产生 4xx/5xx。"""
        cases = [
            {"url": "javascript:alert(1)"},
            {"url": "javascript:alert(1)", "from": "<script>"},
            {"url": ""},
            {},
            {"url": "https://example.com/x", "from": "999999999"},
            {"url": "https://example.com/x", "from": "abc"},
        ]
        for query in cases:
            with self.subTest(query=query):
                response = self.client.get("/api/v1/link-confirm", query)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("ok", data)
                self.assertIn("problem", data)


class PreviewAntiOracleTests(SecurityDataTestCase):
    """E9 反预言机：一切失败路径＝同一 404 状态＋同一响应体（不泄露
    哪一环节失败——票据伪造者无法据此收敛）。"""

    def _editor_session(self):
        store = SessionStore()
        store["_auth_user_id"] = str(self.editor.pk)
        store.create()
        return store.session_key

    def _uniform_failure_responses(self):
        session_key = self._editor_session()
        # 未过期基线票据（FormState 从未创建——兑换仍须 404）。
        valid_shape = _mint(session_key, self.editor.pk, self.notice.pk)
        tampered = valid_shape[:-2] + ("aa" if valid_shape[-2:] != "aa" else "bb")
        cases = {
            "no-token": "/api/v1/preview",
            "empty-token": "/api/v1/preview?token=",
            "short-token": "/api/v1/preview?token=abc",
            "tampered": f"/api/v1/preview?token={tampered}",
            "wrong-salt": "/api/v1/preview?token="
            + _mint(session_key, self.editor.pk, self.notice.pk, salt="other-salt"),
            "wrong-type": "/api/v1/preview?token=" + _mint(session_key, self.editor.pk, 999999),
            "no-formstate": f"/api/v1/preview?token={valid_shape}",
        }
        responses = []
        for label, path in cases.items():
            with self.subTest(mode=label):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "not_found")
                responses.append((response.status_code, response.content))
        return responses

    def test_all_failures_uniform(self):
        responses = self._uniform_failure_responses()
        self.assertTrue(responses)
        self.assertEqual(len(set(responses)), 1)

    def test_expired_token_uniform(self):
        """过期票据（>60s）与其余失败路径同一 404 体。"""
        import unittest.mock

        responses = self._uniform_failure_responses()
        session_key = self._editor_session()
        with unittest.mock.patch("django.core.signing.time.time", return_value=1_000_000.0):
            token = _mint(session_key, self.editor.pk, self.notice.pk)
        with unittest.mock.patch("django.core.signing.time.time", return_value=1_000_061.0):
            response = self.client.get(f"/api/v1/preview?token={token}")
        self.assertEqual((response.status_code, response.content), responses[0])

    def test_deleted_session_uniform(self):
        """票据铸造后会话即注销（编辑器登出）→ 404 与其余路径同体。"""
        responses = self._uniform_failure_responses()
        session_key = self._editor_session()
        token = _mint(session_key, self.editor.pk, self.notice.pk)
        SessionStore(session_key).delete()
        response = self.client.get(f"/api/v1/preview?token={token}")
        self.assertEqual((response.status_code, response.content), responses[0])

    def test_non_content_page_token_uniform(self):
        """票据指向非五类内容页（结构页）→ 404 同体（铸造端同样拒绝）。"""
        responses = self._uniform_failure_responses()
        session_key = self._editor_session()
        root_pk = Site.objects.get(is_default_site=True).root_page.pk
        token = _mint(session_key, self.editor.pk, root_pk)
        response = self.client.get(f"/api/v1/preview?token={token}")
        self.assertEqual((response.status_code, response.content), responses[0])

    def test_content_models_registered_for_preview_gate(self):
        """门控范围＝五类内容页全集（按钮与铸造端同一判定集合）。"""
        from guides.models import GuidePage
        from notices.models import ArticlePage, NoticePage
        from resources.models import MaterialPage, SoftwareToolPage

        self.assertEqual(
            set(SEARCHABLE_PAGE_MODELS),
            {NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage},
        )
