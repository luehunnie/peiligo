"""F-03 外链统一确认页与 scheme 收窄回归（SB §10-7 / CM §11.4 / SEC-21/22 / SB-06 / PRD §7.5）。

断言面：字段层 SB §10-7 七规则（strip／scheme+host 大小写／URLValidator
格式／缺协议不静默补全／userinfo 凭据段／相对与 scheme 相对形式／scheme
白名单 http-https）经校验器直测＋五处出口（通知与文章 external_url、活动
报名链接、资料 external_url、软件工具 source_url、外链块）确认页包装不
裸跳转；确认页 PRD §7.5 四要素（域名/来源/最后更新时间/声明，站点设置
可覆盖）、恒 noindex＋canonical、无自动跳转、不入 sitemap；「继续访问」
端点输出层二次校验通过才 302，开放重定向样本一律拒绝（SEC-22）。
"""

import json
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from home.models import SiteSettings
from home.views import DEFAULT_REDIRECT_NOTICE
from notices.blocks import ExternalLinkBlock
from notices.models import NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from peiligo.link_validation import (
    display_external_url,
    external_url_domain,
    validate_external_url,
)
from tests.helpers import _save, build_sections, future, make_container, make_department


def _body(*blocks):
    return json.loads(json.dumps(list(blocks)))


class ValidateExternalUrlTests(SimpleTestCase):
    """SB §10-7 规则 1–7 逐条（校验器直测）。"""

    def test_accepts_http_https_and_normalizes_case_strip(self):
        self.assertEqual(
            validate_external_url("https://example.com/a?b=1"), "https://example.com/a?b=1"
        )
        self.assertEqual(validate_external_url("http://example.com"), "http://example.com")
        self.assertEqual(validate_external_url("  https://example.com  "), "https://example.com")

    def test_rejects_missing_scheme_without_silent_repair(self):
        """规则 4/6：缺协议与 //host scheme 相对形式拒绝，不静默补全。"""
        for bad in ("www.example.com", "//evil.com", "https:evil.com"):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(ValidationError, "缺少协议"):
                    validate_external_url(bad)

    def test_rejects_non_whitelisted_schemes(self):
        """规则 7：Django URLValidator 默认放行的 ftp 等一律收窄拒绝。"""
        for bad in (
            "ftp://example.com/x",
            "ftps://example.com",
            "javascript:alert(1)",
            "mailto:a@b.com",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    validate_external_url(bad)

    def test_rejects_userinfo_credential_segment(self):
        """规则 5：user:pass@ 凭据段拒绝（防钓鱼混淆）。"""
        with self.assertRaisesMessage(ValidationError, "凭据段"):
            validate_external_url("https://user:pass@evil.com/file")

    def test_rejects_embedded_whitespace(self):
        """规则 1：strip 后仍含空白＝空格夹带拒绝（首尾空白经 strip 容忍）。"""
        for bad in ("https://a b.com", "https://example.com/a b"):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(ValidationError, "空格"):
                    validate_external_url(bad)
        self.assertEqual(
            validate_external_url("  https://example.com/x\n"), "https://example.com/x"
        )

    def test_rejects_malformed_url(self):
        """规则 3：URLValidator 不过（如空 host）拒绝。"""
        with self.assertRaisesMessage(ValidationError, "格式不正确"):
            validate_external_url("https:///path/only")

    def test_blank_is_valid_empty(self):
        self.assertEqual(validate_external_url(""), "")
        self.assertEqual(validate_external_url(None), "")
        self.assertEqual(validate_external_url("   "), "")


class DisplayNormalizeTests(SimpleTestCase):
    """SB §10-7 规则 2：scheme 与 host 小写化的展示与域名提取。"""

    def test_display_lowercases_scheme_and_host_keeps_path(self):
        self.assertEqual(
            display_external_url("HTTPS://EXAMPLE.com/Path?q=1"),
            "https://example.com/Path?q=1",
        )

    def test_domain_lowercased_and_port_stripped(self):
        self.assertEqual(external_url_domain("https://EXAMPLE.com:8443/x"), "example.com")


class FieldWiringTests(SimpleTestCase):
    """接线事实：五处外链出口的字段层全部挂上统一校验器。"""

    def test_four_url_fields_carry_validator(self):
        for model, field_name in (
            (NoticePage, "external_url"),
            (MaterialPage, "external_url"),
            (SoftwareToolPage, "source_url"),
        ):
            with self.subTest(field=f"{model.__name__}.{field_name}"):
                from django.db import models

                field = model._meta.get_field(field_name)
                self.assertIsInstance(field, models.URLField)
                self.assertIn(validate_external_url, field.validators)

    def test_notice_and_article_models_share_field_definition(self):
        """通知与文章的 external_url 同为统一校验（两模型字段各自声明）。"""
        from notices.models import ArticlePage

        for model in (NoticePage, ArticlePage):
            with self.subTest(model=model.__name__):
                self.assertIn(
                    validate_external_url, model._meta.get_field("external_url").validators
                )

    def test_external_link_block_rejects_bad_scheme_on_clean(self):
        """外链块 URLBlock：校验器进入块字段并在块 clean 生效（拒绝语义，
        文案语义由校验器直测锁定）。"""
        url_block = ExternalLinkBlock().child_blocks["url"]
        self.assertIn(validate_external_url, url_block.field.validators)
        with self.assertRaises(ValidationError):
            ExternalLinkBlock().clean({"url": "ftp://example.com", "link_text": "下载"})


class ConfirmPageDataTestCase(WagtailPageTestCase):
    """公共数据：五出口内容各一。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.jwc = make_department("教务处", "jwc")
        cls.container = make_container(cls.sections["chronicle"], cls.jwc)
        # 活动字段（EventFieldsMixin clean）仅活动板块容器可填（§7.2）；
        # 资料/工具页各归其允许板块（§1.4 板块×类型绑定）。
        cls.events_container = make_container(cls.sections["events"], cls.jwc)
        cls.materials_container = make_container(cls.sections["materials"], cls.jwc)
        cls.software_container = make_container(cls.sections["software"], cls.jwc)
        cls.notice = _save(
            NoticePage(
                title="带外链的通知",
                slug="ext-notice",
                summary="测试摘要",
                department=cls.container.department,
                expire_at=future(),
                external_url="https://example.com/doc",
                body=_body({"type": "paragraph", "value": "<p>说明正文。</p>"}),
            ),
            cls.container,
            publish=True,
        )
        cls.event_notice = _save(
            NoticePage(
                title="带报名链接的活动",
                slug="ext-event",
                summary="测试摘要",
                department=cls.container.department,
                expire_at=future(),
                event_start_at=future(days=3),
                event_end_at=future(days=4),
                event_location="大学生活动中心",
                event_registration_url="https://forms.example.com/signup",
                body=_body({"type": "paragraph", "value": "<p>活动说明。</p>"}),
            ),
            cls.events_container,
            publish=True,
        )
        cls.block_notice = _save(
            NoticePage(
                title="带外链块的文章",
                slug="ext-block",
                summary="测试摘要",
                department=cls.container.department,
                expire_at=future(),
                body=_body(
                    {"type": "paragraph", "value": "<p>正文。</p>"},
                    {
                        "type": "external_link",
                        "value": {"url": "https://files.example.com/setup", "link_text": "安装包"},
                    },
                ),
            ),
            cls.container,
            publish=True,
        )
        cls.material = _save(
            MaterialPage(
                title="带外链的资料",
                slug="ext-material",
                summary="测试摘要",
                department=cls.container.department,
                discipline_id=cls._discipline_pk(),
                material_type_id=cls._material_type_pk(),
                external_url="https://pan.example.com/file",
                body=_body({"type": "paragraph", "value": "<p>资料说明。</p>"}),
            ),
            cls.materials_container,
            publish=True,
        )
        cls.software = _save(
            SoftwareToolPage(
                title="带来源链接的工具",
                slug="ext-software",
                department=cls.container.department,
                platforms=cls._platforms(),
                source_url="https://vendor.example.com/setup",
                license_note="校园授权，免费使用",
                body=_body({"type": "paragraph", "value": "<p>工具说明。</p>"}),
            ),
            cls.software_container,
            publish=True,
        )

    @classmethod
    def _discipline_pk(cls):
        from resources.models import Discipline

        return Discipline.objects.get_or_create(name="计算机科学")[0].pk

    @classmethod
    def _material_type_pk(cls):
        from resources.models import MaterialType

        return MaterialType.objects.get_or_create(name="课件")[0].pk

    @classmethod
    def _platforms(cls):
        from resources.models import Platform

        return [Platform.objects.get_or_create(name="Windows")[0]]

    def _confirm_href(self, url, page_pk):
        # 模板侧 urlencode 过滤器＝quote(value, safe="/")
        return f"/link-confirm/?url={quote(url, safe='/')}&from={page_pk}"


class OutletWrapTests(ConfirmPageDataTestCase):
    """五处出口：外链一律确认页包装，无裸跳转 <a>。"""

    def _assert_wrapped(self, page, raw_url):
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self._confirm_href(raw_url, page.pk))
        self.assertNotContains(response, f'<a href="{raw_url}"')

    def test_notice_external_url_wrapped(self):
        self._assert_wrapped(self.notice, "https://example.com/doc")

    def test_event_registration_url_wrapped(self):
        self._assert_wrapped(self.event_notice, "https://forms.example.com/signup")

    def test_material_external_url_wrapped(self):
        self._assert_wrapped(self.material, "https://pan.example.com/file")

    def test_software_source_url_wrapped(self):
        self._assert_wrapped(self.software, "https://vendor.example.com/setup")

    def test_external_link_block_wrapped(self):
        response = self.client.get(self.block_notice.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, self._confirm_href("https://files.example.com/setup", self.block_notice.pk)
        )
        self.assertContains(response, "安装包")

    def test_block_url_is_validated_at_save(self):
        """外链块存坏 URL（scheme 白名单外）＝保存期拒绝。"""
        page = NoticePage(
            title="坏外链块",
            slug="bad-block",
            summary="测试摘要",
            department=self.container.department,
            expire_at=future(),
            body=_body(
                {"type": "external_link", "value": {"url": "ftp://example.com", "link_text": "坏"}}
            ),
        )
        with self.assertRaises(ValidationError):
            page.full_clean()


class ConfirmPageTests(ConfirmPageDataTestCase):
    """确认页本体：四要素＋恒 noindex＋无自动跳转。"""

    def test_four_elements_rendered(self):
        response = self.client.get(
            "/link-confirm/", {"url": "https://example.com/doc", "from": str(self.notice.pk)}
        )
        self.assertEqual(response.status_code, 200)
        # Phase 8D 展示口径：目标只展示主机名（域名），不展示完整 URL。
        self.assertContains(response, 'c-domain">example.com<')
        self.assertNotContains(response, "https://example.com/doc")
        self.assertContains(response, "带外链的通知")  # 来源
        self.assertContains(response, "最后更新时间")
        self.assertContains(response, DEFAULT_REDIRECT_NOTICE)
        self.assertContains(response, "/link-confirm/go/?url=https%3A%2F%2Fexample.com%2Fdoc")
        self.assertContains(response, "继续访问")
        self.assertContains(response, "返回")

    def test_display_is_case_normalized(self):
        """SB §10-7 规则 2：host 小写化展示（Phase 8D＝仅域名），完整 URL
        不以明文出页面（页脚 mailto 回执中的百分号编码回显不属展示文本）。"""
        response = self.client.get("/link-confirm/", {"url": "HTTPS://EXAMPLE.com/Path?q=1"})
        self.assertContains(response, 'c-domain">example.com<')
        self.assertNotContains(response, "HTTPS://EXAMPLE.com/Path?q=1")
        self.assertNotContains(response, "Path?q=1")

    def test_confirm_page_title_and_copy(self):
        """Phase 8D 定稿文案：kicker／标题／说明／主次按钮。"""
        response = self.client.get("/link-confirm/", {"url": "https://example.com/doc"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "外部链接")
        self.assertContains(response, "即将访问外部网站")
        self.assertContains(response, "你将离开 Peiligo，前往第三方网站。")
        self.assertContains(response, "继续访问")
        self.assertContains(response, "返回 Peiligo")

    def test_no_inline_js_and_no_auto_redirect(self):
        """无 inline JS／javascript:／meta refresh——合法目标与拒绝态均然。"""
        for params in (
            {"url": "https://example.com/doc", "from": str(self.notice.pk)},
            {"url": "https://example.com/doc"},
            {"url": "javascript:alert(1)"},
        ):
            with self.subTest(params=params):
                response = self.client.get("/link-confirm/", params)
                self.assertEqual(response.status_code, 200)
                content = response.content.decode()
                self.assertNotIn("onclick=", content)
                self.assertNotIn("javascript:", content)
                self.assertNotIn("<script", content)
                self.assertNotIn("http-equiv", content)

    def test_return_action_is_deterministic_internal(self):
        """「返回 Peiligo」＝确定性站内链接：有来源页→来源页，否则首页；
        绝不回退到外部来源参数。"""
        with_source = self.client.get(
            "/link-confirm/", {"url": "https://example.com/doc", "from": str(self.notice.pk)}
        )
        self.assertContains(with_source, '<a class="c-ghost" href="/chronicle/jwc/ext-notice/">')
        without_source = self.client.get("/link-confirm/", {"url": "https://example.com/doc"})
        self.assertContains(without_source, '<a class="c-ghost" href="/">')
        content = without_source.content.decode()
        self.assertNotIn('href="https://example.com', content)

    def test_custom_notice_text_from_site_settings(self):
        site = Site.objects.get(is_default_site=True)
        SiteSettings.objects.create(site=site, redirect_notice_text="自定义第三方声明文案XYZ")
        response = self.client.get("/link-confirm/", {"url": "https://example.com/doc"})
        self.assertContains(response, "自定义第三方声明文案XYZ")
        self.assertNotContains(response, DEFAULT_REDIRECT_NOTICE)

    def test_missing_or_bad_from_omits_source_elements(self):
        for bad_from in ("abc", "999999", ""):
            with self.subTest(from_=bad_from):
                response = self.client.get(
                    "/link-confirm/", {"url": "https://example.com/doc", "from": bad_from}
                )
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "最后更新时间")
                self.assertNotContains(response, "来源")

    def test_draft_or_expired_source_page_not_disclosed(self):
        """R 审查 M3：from 仅引用前台可见页——草稿/到期页标题零泄漏。"""
        draft = self.notice  # 复用同一容器下另建草稿
        from tests.helpers import make_notice

        draft = make_notice(self.container, slug="confirm-draft-src")
        expired = make_notice(self.container, slug="confirm-expired-src", publish=True)
        expired.expired = True
        expired.save()

        for hidden, label in ((draft, "草稿"), (expired, "到期")):
            with self.subTest(state=label):
                response = self.client.get(
                    "/link-confirm/",
                    {"url": "https://example.com/doc", "from": str(hidden.pk)},
                )
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "最后更新时间")
                self.assertNotContains(response, hidden.title)

        # live 在场页仍正常披露（行为不回缩）
        live = make_notice(self.container, slug="confirm-live-src", publish=True)
        response = self.client.get(
            "/link-confirm/", {"url": "https://example.com/doc", "from": str(live.pk)}
        )
        self.assertContains(response, live.title)

    def test_noindex_and_canonical_always(self):
        """确认页恒 noindex＋canonical 指向去参基础 URL（IA §10 家族）。"""
        for params in ({"url": "https://example.com/doc"}, {}):
            with self.subTest(params=params):
                response = self.client.get("/link-confirm/", params)
                self.assertContains(response, '<meta name="robots" content="noindex">')
                self.assertContains(
                    response, 'rel="canonical" href="http://testserver/link-confirm/"'
                )

    def test_no_auto_redirect(self):
        response = self.client.get("/link-confirm/", {"url": "https://example.com/doc"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Location", response)
        self.assertNotIn("refresh", response.content.decode().lower())

    def test_invalid_target_rejected_with_reason(self):
        cases = [
            ("ftp://example.com/x", "仅支持"),
            ("//evil.com", "缺少协议"),
            ("https:evil.com", "缺少协议"),
            ("javascript:alert(1)", "缺少协议"),
            ("https://user:pass@evil.com", "凭据段"),
            ("https://a b.com", "空格"),
        ]
        for bad, fragment in cases:
            with self.subTest(bad=bad):
                response = self.client.get("/link-confirm/", {"url": bad})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "不安全或格式不正确")
                self.assertContains(response, fragment)
                self.assertNotContains(response, "继续访问")
                self.assertContains(response, '<meta name="robots" content="noindex">')


class GoEndpointTests(ConfirmPageDataTestCase):
    """「继续访问」端点：输出层二次校验（SB §10-7 校验位置条）。"""

    def test_valid_target_redirects_302(self):
        response = self.client.get("/link-confirm/go/", {"url": "https://example.com/doc"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://example.com/doc")

    def test_invalid_targets_never_redirect(self):
        """SEC-22：开放重定向样本一律渲染拒绝页，不产生跳转。"""
        for bad in (
            "//evil.com",
            "https:evil.com",
            "ftp://example.com",
            "javascript:alert(1)",
            "https://user:pass@evil.com",
            "https:///path",
        ):
            with self.subTest(bad=bad):
                response = self.client.get("/link-confirm/go/", {"url": bad})
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("Location", response)
                self.assertContains(response, "不安全或格式不正确")


class SitemapExclusionTests(ConfirmPageDataTestCase):
    """确认页不入 sitemap（自定义视图不在页面树，IA-03 同语义显式断言）。"""

    def test_link_confirm_absent_from_sitemap(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/link-confirm")
