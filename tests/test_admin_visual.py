"""AVR② admin 视觉回归（ADMIN_VISUAL_RECOVERY_CONTRACT §2–§11）。

轻量行为面：不做像素快照，只锁三类可回归事实——
1. 扩展点在位：insert_global_admin_css 注入本文件且晚于 core.css（§11 降级原则）；
2. 品牌与 i18n：侧栏字标、登录页中文标签、项目级 locale 目录逐 msgid 生效（§3/§9）；
3. CSS 自检：主题四象限齐全、无 !important、:root 仅承载品牌令牌与字体栈
   （防级联回退：晚加载的裸 :root 会压过 core 的 .w-theme-dark，§8）。
"""

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

CSS_PATH = Path(__file__).resolve().parent.parent / "static" / "css" / "admin.css"
PASSWORD = "avr2-visual-123"


class AdminVisualBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            username="avr2-visual", password=PASSWORD, email="avr2@peiligo.test"
        )

    def login(self):
        client = self.client
        assert client.login(username="avr2-visual", password=PASSWORD)
        return client


class AdminCssInjectionTests(AdminVisualBase):
    """§11 扩展点：唯一 CSS 注入路径与加载顺序。"""

    def test_admin_css_injected_after_core_on_home(self):
        client = self.login()
        html = client.get(reverse("wagtailadmin_home")).content.decode()
        core = html.index("wagtailadmin/css/core.css")
        ours = html.find("css/admin.css")
        self.assertGreater(ours, core, "admin.css 必须晚于 core.css 注入（同特异性才让位）")
        self.assertGreater(ours, -1, "insert_global_admin_css 未注入 admin.css")

    def test_admin_css_injected_on_explorer(self):
        client = self.login()
        html = client.get(reverse("wagtailadmin_explore_root")).content.decode()
        self.assertIn("css/admin.css", html)


class BrandingTests(AdminVisualBase):
    """§3 品牌：侧栏字标与登录页。"""

    def test_sidebar_branding_lockup_wired_in_dashboard(self):
        """侧栏本体由 sidebar.js 按 #wagtail-sidebar-props 客户端渲染；
        服务端事实=branding-logo 模板就位并携带方章字标。"""
        client = self.login()
        html = client.get(reverse("wagtailadmin_home")).content.decode()
        self.assertIn("data-wagtail-sidebar-branding-logo", html)
        self.assertIn("plg-brand__mark", html)
        self.assertIn("Peiligo", html)

    def test_login_page_branding_and_chinese_labels(self):
        html = self.client.get(reverse("wagtailadmin_login")).content.decode()
        self.assertIn("登录 Peiligo", html, "branding_login 块应为中文品牌标题")
        self.assertIn("用户名", html, "登录字段标签应为中文（label_text 直给）")
        self.assertIn("密码", html)
        self.assertIn("plg-brand__mark", html)

    def test_dashboard_search_submit_value_is_chinese(self):
        """AVR③-fix D4：sr-only 搜索提交按钮 value 中文化（上游硬编码无 trans）。"""
        client = self.login()
        html = client.get(reverse("wagtailadmin_home")).content.decode()
        self.assertIn('value="搜索"', html)
        self.assertNotIn('value="Search"', html)


class LocaleResidualTests(TestCase):
    """§9 i18n 残留：项目级 zh_Hans 目录逐 msgid 补译（LOCALE_PATHS 优先合并）。"""

    def test_schedule_dialog_and_sidebar_strings_translated(self):
        with translation.override("zh-hans"):
            cases = [
                ("Search all pages…", "搜索所有页面…"),
                ("Publish now", "立即发布"),
                ("Schedule to publish", "定时发布"),
                (
                    "This publishing schedule will only take effect after you"
                    ' select the "Schedule to publish" option',
                    "此发布时间表只有在选择“定时发布”选项后才会生效",
                ),
                (
                    "Anyone can edit this %(model_name)s – lock it to prevent others from editing",
                    "任何人都可以编辑此%(model_name)s——锁定可防止其他人编辑",
                ),
                (
                    "Wagtail %(current_version)s editor guide",
                    "Wagtail %(current_version)s 编辑指南",
                ),
            ]
            for msgid, expected in cases:
                self.assertEqual(translation.gettext(msgid), expected, msg=f"未补译：{msgid!r}")

    def test_plural_strings_translated_with_ngettext(self):
        """复数条目存于 (msgid, plural) 键下，须以 ngettext 验证（§9）。"""
        from django.utils.translation import ngettext

        with translation.override("zh-hans"):
            got = ngettext("Referenced %(count)s time", "Referenced %(count)s times", 3) % {
                "count": 3
            }
            self.assertEqual(got, "被引用 3 次")
            got = ngettext(
                '%(total)s Page <span class="w-sr-only">created in %(site_name)s</span>',
                '%(total)s Pages <span class="w-sr-only">created in %(site_name)s</span>',
                11,
            ) % {"total": 11, "site_name": "Peiligo"}
            self.assertEqual(
                got,
                '11 个页面<span class="w-sr-only">（Peiligo 内）</span>',
            )

    def test_avr3_fix_defects_translated(self):
        """AVR③-fix D1/D4：explorer root 横幅、分页统计、升级横幅逐 msgid 补译。"""
        cases = [
            # D1：explorer root 层提示横幅（explorable_index_results.html）
            (
                "The root level is where you can add new sites to your Wagtail"
                " installation. Pages created here will not be accessible at any"
                " URL until they are associated with a site.",
                "根层级用于为 Wagtail 安装实例添加新站点。在此创建的页面在关联站点之前，"
                "将无法通过任何 URL 访问。",
            ),
            (
                "If you just want to add pages to an existing site, create them"
                " as children of the homepage instead.",
                "如果只是想向现有站点添加页面，请改为在首页下创建子页面。",
            ),
            (
                "Pages created here will not be accessible at any URL. To add"
                " pages to an existing site, create them as children of the"
                " homepage.",
                "在此创建的页面将无法通过任何 URL 访问。"
                "若要向现有站点添加页面，请在首页下创建子页面。",
            ),
            # D1：分页统计（_page_title_column_header.html 三个 scope 变体）
            (
                "%(start_index)s-%(end_index)s of %(items_count)s %(model_name)s",
                "第 %(start_index)s-%(end_index)s 项，共 %(items_count)s 个%(model_name)s",
            ),
            (
                "%(start_index)s-%(end_index)s of %(items_count)s %(model_name)s"
                " across entire site.",
                "第 %(start_index)s-%(end_index)s 项，共 %(items_count)s 个%(model_name)s"
                "（整站范围）。",
            ),
            # D4：升级提示横幅（home/upgrade_notification.html）
            ("Wagtail upgrade available", "Wagtail 有可用升级"),
            ("Read the release notes.", "阅读版本说明。"),
        ]
        with translation.override("zh-hans"):
            for msgid, expected in cases:
                self.assertEqual(translation.gettext(msgid), expected, msg=f"未补译：{msgid!r}")


class AdminCssSelfChecks(TestCase):
    """§8/§11 CSS 结构自检：四象限齐全 + 禁 !important + :root 不越权。"""

    def setUp(self):
        self.css = CSS_PATH.read_text(encoding="utf-8")

    def test_theme_quadrants_present(self):
        self.assertIn(".w-theme-light {", self.css)
        self.assertIn(".w-theme-dark {", self.css)
        self.assertEqual(
            self.css.count(".w-theme-system {"), 2, "system 主题须按浅/深媒体查询各写一份"
        )
        self.assertEqual(
            self.css.count("--w-color-secondary-75:"), 4, "四象限各钉一次 secondary-75"
        )
        self.assertEqual(self.css.count("--w-color-secondary-hue:"), 4)

    def test_avr3_fix_dark_info_token_and_title_converged(self):
        """AVR③-fix D2/D3：深色象限各钉一行 info-50；编辑器标题字号收敛一条规则。"""
        self.assertEqual(
            self.css.count("--w-color-info-50:"),
            2,
            "info-50 须在两个深色象限各钉一次（.w-theme-dark 与 system+深色 OS）",
        )
        title_rule = re.search(
            r"\.w-panel\.title:nth-child\(-n\+2\) :is\([^)]*\)[^{}]*\{[^}]*\}", self.css
        )
        self.assertIsNotNone(title_rule, "D3：须有编辑器标题字号收敛规则")
        self.assertIn("font-size: 1.5rem", title_rule.group(0))

    def test_no_important_and_root_holds_only_brand_tokens(self):
        rules = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S)  # 只查规则区，头注提及该禁令本身
        self.assertNotIn("!important", rules, "契约 §11：禁成批 !important")
        for block in re.findall(r":root\s*\{[^}]*\}", self.css):
            for line in block.splitlines():
                if "--w-" in line:
                    self.assertIn(
                        "--w-font-sans",
                        line,
                        ":root 内不得覆写 --w-*（晚加载的裸 :root 会压过 core 的 .w-theme-dark）",
                    )
