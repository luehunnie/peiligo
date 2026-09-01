"""M-1+L-11（Final Fix）：反馈邮箱取值契约测试。

站点设置（后台 M-E1 可改单值）优先，环境缺省兜底；设置/站点行缺失
fail-soft 回落——前台渲染永不因设置缺失而 500。优先级经 HTTP 在
页脚/首页/404 三个消费面断言（与 FooterToolEntriesTests 同口径）。
"""

from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from home.models import SiteSettings
from wagtail.models import Site

from peiligo.context_processors import site_chrome

SITE_EMAIL = "site-admin@example.edu"


class FeedbackEmailPriorityTests(TestCase):
    """站点设置值 > 空值回落环境缺省 > 行缺失 fail-soft。"""

    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_sections", stdout=StringIO())
        cls.site = Site.objects.get(is_default_site=True)

    def _row(self):
        return SiteSettings.for_site(self.site)

    def test_site_settings_value_takes_priority(self):
        """站点设置值非空 → 前台三个消费面均用它而非环境缺省。"""
        SiteSettings.objects.filter(pk=self._row().pk).update(feedback_email=SITE_EMAIL)
        for url in ("/", "/chronicle/", "/no-such-page/"):
            with self.subTest(url=url):
                resp = self.client.get(url)
                status = resp.status_code
                self.assertIn(status, (200, 404))
                self.assertContains(resp, f"mailto:{SITE_EMAIL}", status_code=status)
                self.assertNotContains(
                    resp, f"mailto:{settings.FEEDBACK_EMAIL}", status_code=status
                )

    def test_empty_site_settings_falls_back_to_env(self):
        """站点设置值为空串 → 回落环境缺省（settings.FEEDBACK_EMAIL）。"""
        SiteSettings.objects.filter(pk=self._row().pk).update(feedback_email="")
        resp = self.client.get("/")
        self.assertContains(resp, f"mailto:{settings.FEEDBACK_EMAIL}")
        self.assertNotContains(resp, f"mailto:{SITE_EMAIL}")

    def test_missing_site_row_fail_soft(self):
        """站点行缺失（Site.DoesNotExist）→ 处理器回落环境缺省、不抛错。"""
        Site.objects.all().delete()
        result = site_chrome(RequestFactory().get("/"))
        self.assertEqual(result["feedback_email"], settings.FEEDBACK_EMAIL)
