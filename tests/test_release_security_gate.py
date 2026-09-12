"""Phase 9 · 发布安全门回归（CSP／favicon／反馈邮件隐私／highlight 边角）。

对应 Phase 9 审计四项收口：

- CSP（C 项）：公开响应带最小 Content-Security-Policy（default-src 'self'
  起、object-src 'none'），管理面前缀（/admin/、/django-admin/）豁免；
  404 动态响应同样盖章。
- favicon（P 项）：/favicon.ico 301 落既有校徽静态资产；base.html 声明
  link rel=icon。
- 反馈邮件隐私（Q 项）：外链确认页页脚 mailto 正文只含站内路径——当前
  URL 查询串即外链目标本体（可携敏感 token），不得自动进入反馈邮件；
  普通页面（无敏感查询语义）保留完整绝对地址正文。
- highlight（E 项）：正则元字符 query／含 HTML 语法的命中片段在
  escape-before-mark 管线下的边角回归（主回归见
  tests/test_frontend_foundation.py）。
"""

import re

from django.template import Context, Template
from django.test import SimpleTestCase, TestCase

CSP_HEADER = "Content-Security-Policy"


class ContentSecurityPolicyHeaderTests(TestCase):
    """C 项：公开面最小 CSP；管理面豁免；404 同盖。"""

    def test_public_response_carries_policy(self):
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        policy = response.headers.get(CSP_HEADER, "")
        for directive in (
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data:",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'self'",
            "form-action 'self'",
        ):
            self.assertIn(directive, policy)

    def test_admin_prefixes_exempt(self):
        for path in ("/admin/login/", "/django-admin/login/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertNotIn(CSP_HEADER, response.headers)

    def test_404_response_still_carries_policy(self):
        response = self.client.get("/nonexistent-path-404/")
        self.assertEqual(response.status_code, 404)
        self.assertIn(CSP_HEADER, response.headers)


class FaviconTests(TestCase):
    """P 项：/favicon.ico 缺位消除，图标＝既有官方校徽资产。"""

    def test_favicon_redirects_to_existing_asset(self):
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/static/img/peiligo-school-logo.png")

    def test_base_html_declares_icon_link(self):
        response = self.client.get("/search/")
        self.assertIn(b'<link rel="icon" type="image/png"', response.content)


class FeedbackMailtoPrivacyTests(TestCase):
    """Q 项：确认页 mailto 不携带外链目标；普通页保留完整地址正文。"""

    def test_confirm_page_mailto_body_is_internal_path_only(self):
        target = "https://external.example/doc?token=SECRET-TOKEN"
        response = self.client.get("/link-confirm/", {"url": target})
        self.assertEqual(response.status_code, 200)
        hrefs = re.findall(rb'href="mailto:[^"]*"', response.content)
        self.assertEqual(len(hrefs), 1)
        mailto = hrefs[0]
        # 正文只含站内路径。
        self.assertIn(b"body=/link-confirm/", mailto)
        # 任一 mailto 不得夹带目标 URL／其查询 token。
        self.assertNotIn(b"external.example", mailto)
        self.assertNotIn(b"SECRET-TOKEN", mailto)

    def test_regular_page_mailto_keeps_absolute_uri(self):
        """非确认页（无敏感查询语义）正文仍为完整绝对地址（反馈可点击回溯）。"""
        response = self.client.get("/search/", {"q": "测试"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"body=http%3A//testserver/search/", response.content)


class HighlightEdgeCaseTests(SimpleTestCase):
    """E 项边角：正则元字符 query 与含 HTML 语法命中片段均不得逃逸。"""

    def _render(self, text, q):
        return Template("{% load peiligo_extras %}{{ t|highlight:q }}").render(
            Context({"t": text, "q": q})
        )

    def test_regex_metachar_query_is_literal_and_escaped(self):
        rendered = self._render("价格 <b>99.50</b> 元", "99.50")
        self.assertEqual(rendered, "价格 &lt;b&gt;<mark>99.50</mark>&lt;/b&gt; 元")

    def test_metachar_only_query_never_crashes_or_leaks(self):
        query = ".*+?[]{}|\\^$()"
        rendered = self._render(f"<script>{query}</script>", query)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_case_insensitive_hit_is_marked_and_escaped(self):
        rendered = self._render("Risk &amp; Co", "RISK")
        self.assertEqual(rendered, "<mark>Risk</mark> &amp;amp; Co")
