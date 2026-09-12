"""首页轮播 JS 渐进增强契约测试（首页升级 Phase 7；ADR-0007）。

断言面（Phase 7 TASK P 清单；SSR/资产层契约，不引入任何 JS 测试框架）：

- 脚本加载（TASK K）：首页 script 仅本地 static/js/carousel.js 且 defer；
  零 CDN／远程脚本；板块页与 /search/ 零 script（仅首页加载）；
- JS 资产（TASK P #9）：文件真实存在于 static 并承载轮播 hook 契约；
  轻量源码契约断言（eval/new Function/innerHTML/document.write/onclick/
  远程 URL 零出现——普通字符串误报面由测试数据封闭，非整文件快照）；
- 初始化事务性（Phase 7 failure-safe fix）：增强提交阶段包在 try 内，任一
  步骤失败必须存在回滚保证——unhide 全部条目、清除 active/aria-current、
  移除已插入控件、摘除增强标记、停 autoplay，enhanced 闸门使 handler／
  autoplay 之后安全 no-op（PARTIAL_INIT_FAILURE_FALLBACK ≡ NO_JS_FALLBACK）；
- SSR 纯度（TASK N）：server HTML 不带 hidden、不输出任何 controls（控件
  仅 JS 动态创建——无 JS 不留死按钮）、不预置增强标记
  data-carousel-enhanced、无 inline onclick；
- 条目输出（Phase 6 契约不回退）：1 项静态输出、2–5 项全部文档流输出；
- 外链确认链路不受影响（F-03：carousel 外链仍走 /link-confirm/）；
- base.html 旧「全站无 JS」架构注释已更新为 ADR-0007 口径（TASK L）。

JS 行为本身（autoplay/pause/切换/reduced-motion）按 Phase 7 决策留待
Phase 8 Playwright 真实浏览器验收，本文件不做源码外伪造。
"""

import re
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import SimpleTestCase
from home.models import CAROUSEL_MAX_ITEMS, CarouselItem, SectionPage
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import make_container, make_department, make_notice

# 脚本 src 提取（含 src 的 script 标签，供「仅本地且仅首页」断言）。
SCRIPT_SRC_PATTERN = r'<script\b[^>]*\bsrc="([^"]*)"'

# 轻量危险面清单（静态源码契约；字符串级精确匹配，人工可复核）。
FORBIDDEN_JS_MARKERS = (
    "eval(",
    "new Function",
    "innerHTML",
    "document.write",
    "onclick=",
    "http://",
    "https://",
)

# 扫描前剥离 JS 注释：安全文档在注释里提及禁词（如「不得使用 innerHTML」）
# 属合法内容——TASK O 口径＝普通字符串/文档需人工判断，不凭 grep 无脑
# FAIL；契约只对真实代码面断言。剥离为轻量实现（不解析字符串字面量，
# 本文件无含 "//" 的字符串），非通用 JS 解析器。
JS_COMMENT_PATTERN = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)


class CarouselJsTestCase(WagtailPageTestCase):
    """公共基类：五板块就位＋纪事容器（与首页数据区测试同款装置）。"""

    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_sections", stdout=StringIO())
        cls.sections = {s.slug: s for s in SectionPage.objects.all()}
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.sections["chronicle"], cls.department)

    @staticmethod
    def _carousel_section(html: str) -> str:
        """截取 data-carousel 的 <section>…</section> 片段（区块不嵌套）。"""
        match = re.search(r"<section[^>]*data-carousel[^>]*>(.*?)</section>", html, re.DOTALL)
        return match.group(1) if match else ""

    def _add_internal_item(self, slug: str, title: str) -> None:
        notice = make_notice(self.container, slug=slug, title=title, publish=True)
        CarouselItem(internal_page=notice).save()

    def _add_external_item(self) -> None:
        item = CarouselItem(
            external_url="https://example.com/carousel", external_title="外链标题EX"
        )
        item.save()


class CarouselScriptLoadingTests(CarouselJsTestCase):
    """TASK K：仅首页、仅本地 static、defer 加载 carousel.js。"""

    def test_homepage_loads_exactly_one_local_script_with_defer(self):
        html = self.client.get("/").content.decode()
        self.assertEqual(
            re.findall(SCRIPT_SRC_PATTERN, html),
            ["/static/js/carousel.js"],
        )
        script_tag = re.search(r'<script\b[^>]*src="/static/js/carousel\.js"[^>]*>', html)
        self.assertIsNotNone(script_tag)
        self.assertIn("defer", script_tag.group(0))

    def test_no_cdn_or_remote_script_on_homepage(self):
        html = self.client.get("/").content.decode()
        srcs = re.findall(SCRIPT_SRC_PATTERN, html)
        self.assertTrue(srcs, "首页应至少加载 carousel.js")
        for src in srcs:
            with self.subTest(src=src):
                self.assertTrue(src.startswith("/static/"), f"非本地静态脚本：{src}")

    def test_carousel_js_not_loaded_on_other_public_pages(self):
        for url in ("/chronicle/", "/search/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(re.findall(SCRIPT_SRC_PATTERN, response.content.decode()), [])


class CarouselAssetTests(SimpleTestCase):
    """TASK P #9：JS 文件真实存在于 static；轻量源码安全契约（TASK O）。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = finders.find("js/carousel.js")
        assert path is not None, "static/js/carousel.js 未被 staticfiles 发现"
        cls.script_content = JS_COMMENT_PATTERN.sub("", Path(path).read_text(encoding="utf-8"))

    def test_carousel_js_exists_in_static_with_contract_hooks(self):
        self.assertIn("[data-carousel]", self.script_content)
        self.assertIn("[data-carousel-item]", self.script_content)
        self.assertIn("5500", self.script_content)  # 冻结间隔（TASK F）

    def test_carousel_js_has_no_forbidden_runtime_markers(self):
        for forbidden in FORBIDDEN_JS_MARKERS:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.script_content)


class CarouselFailureSafeContractTests(SimpleTestCase):
    """Phase 7 fix：初始化事务性源码契约（PARTIAL_INIT_FAILURE_FALLBACK）。

    JS 已执行但提交阶段（activate→append→标记→autoplay）任一步骤抛错时，
    源码必须具备等价回滚保证：恢复全部 SSR 条目可见、清除 active 残留与
    dots aria-current、移除已插入控件、摘除 data-carousel-enhanced、停掉
    autoplay，并以 enhanced 闸门使后续 handler／autoplay 安全 no-op——
    失败后的 DOM 状态等价于「JS 未成功增强」（与 NO_JS_FALLBACK 一致）。
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = finders.find("js/carousel.js")
        assert path is not None, "static/js/carousel.js 未被 staticfiles 发现"
        cls.script_content = JS_COMMENT_PATTERN.sub("", Path(path).read_text(encoding="utf-8"))

    def test_rollback_path_restores_full_ssr_state(self):
        """rollback 路径：unhide 全部条目＋清 active/aria-current＋移除控件与标记＋停 autoplay。"""
        self.assertIn("function rollback", self.script_content)
        self.assertIn("slide.hidden = false", self.script_content)
        self.assertIn('classList.remove("is-active")', self.script_content)
        self.assertIn('removeAttribute("aria-current")', self.script_content)
        self.assertIn("removeChild(controls)", self.script_content)
        self.assertIn('removeAttribute("data-carousel-enhanced")', self.script_content)
        self.assertIn("stopAutoplay();", self.script_content)

    def test_commit_phase_is_try_wrapped_and_rolls_back_on_error(self):
        """提交序列（activate→append→标记→autoplay）整体包 try；异常即 rollback＋安全 return。"""
        commit = re.search(
            r"try \{(.*?)\} catch \((?:error|err)\) \{(.*?)\}", self.script_content, re.DOTALL
        )
        self.assertIsNotNone(commit, "增强提交阶段必须包在 try 块中")
        commit_body, catch_body = commit.group(1), commit.group(2)
        # 提交顺序冻结：首个 SSR 可见性改写 → 控件插入 → 增强标记 → autoplay。
        self.assertLess(
            commit_body.index("activate(0)"),
            commit_body.index("appendChild(controls)"),
        )
        self.assertLess(
            commit_body.index("appendChild(controls)"),
            commit_body.index("data-carousel-enhanced"),
        )
        self.assertLess(
            commit_body.index("data-carousel-enhanced"),
            commit_body.index("refreshAutoplay()"),
        )
        # 异常路径：rollback 后安全 return（不显示错误、不再继续增强）。
        self.assertIn("rollback();", catch_body)
        self.assertIn("return;", catch_body)

    def test_enhanced_guard_noops_autoplay_and_navigation_after_rollback(self):
        """enhanced 闸门：回滚后 autoplay 重建与手动导航必须先于任何 DOM 操作 no-op。"""
        self.assertIn("var enhanced = false;", self.script_content)
        # autoplay 重建前必须有 !enhanced 闸门（hover/focus/visibility/motion
        # 事件路径全部经 refreshAutoplay 收口）。
        refresh_start = self.script_content.index("function refreshAutoplay")
        interval_index = self.script_content.index("window.setInterval", refresh_start)
        self.assertIn("!enhanced", self.script_content[refresh_start:interval_index])
        # 手动导航必须先于 activate（SSR 可见性改写）判断 !enhanced。
        goto_start = self.script_content.index("function goTo")
        activate_call = self.script_content.index("activate((targetIndex", goto_start)
        self.assertIn("!enhanced", self.script_content[goto_start:activate_call])


class CarouselServerPurityTests(CarouselJsTestCase):
    """TASK N：JS 初始化前 SSR 保持纯文档流（无 hidden/controls/增强标记）。"""

    def test_single_item_static_no_controls_no_hidden(self):
        """1 项：SSR 单项输出，零 controls／hidden／增强标记（TASK P #4/#6）。"""
        self._add_internal_item("p7-single", "单项通知P7")
        html = self.client.get("/").content.decode()
        section = self._carousel_section(html)
        self.assertNotEqual(section, "")
        self.assertEqual(section.count("data-carousel-item"), 1)
        self.assertNotIn("<button", section)
        self.assertNotIn("data-carousel-controls", section)
        self.assertNotIn("hidden", section)
        self.assertNotIn("data-carousel-enhanced", html)

    def test_multi_items_all_output_without_hidden_or_controls(self):
        """3 项：SSR 全部输出、全部可点链接，零 hidden／controls（TASK P #5/#6）。"""
        for i in range(3):
            self._add_internal_item(f"p7-multi-{i}", f"多项通知{i}")
        html = self.client.get("/").content.decode()
        section = self._carousel_section(html)
        self.assertEqual(section.count("data-carousel-item"), 3)
        self.assertEqual(section.count("<a "), 3)
        self.assertNotIn("hidden", section)
        self.assertNotIn("<button", section)

    def test_two_items_all_output(self):
        self._add_internal_item("p7-two-a", "两项通知A")
        self._add_internal_item("p7-two-b", "两项通知B")
        section = self._carousel_section(self.client.get("/").content.decode())
        self.assertEqual(section.count("data-carousel-item"), 2)

    def test_five_items_all_output(self):
        for i in range(5):
            self._add_internal_item(f"p7-five-{i}", f"五项通知{i}")
        section = self._carousel_section(self.client.get("/").content.decode())
        self.assertEqual(section.count("data-carousel-item"), CAROUSEL_MAX_ITEMS)

    def test_no_inline_onclick_in_server_html(self):
        """TASK P #7：server HTML 零 inline onclick（Phase 7 不得新增）。"""
        self._add_internal_item("p7-onclick", "内联事件通知")
        html = self.client.get("/").content.decode()
        self.assertNotIn("onclick=", html)

    def test_external_item_still_uses_link_confirm_href(self):
        """TASK P #8：JS 引入不旁路外链确认链路（F-03 契约不变）。"""
        self._add_external_item()
        section = self._carousel_section(self.client.get("/").content.decode())
        self.assertIn("/link-confirm/?url=", section)
        # 模板 autoescape 下 href 内 & 渲染为 &amp;（SSR 既有口径不变）。
        self.assertIn("from=", section)


class BaseTemplateCommentTests(SimpleTestCase):
    """TASK L：base.html 旧「全站无 JS」架构注释更新为 ADR-0007 口径。"""

    def test_zero_js_comment_replaced_with_adr0007_wording(self):
        content = (Path(settings.BASE_DIR) / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertNotIn("全站无 JS", content)
        self.assertIn("ADR-0007", content)
        self.assertIn("渐进增强", content)
        # 注入点本体不得被移除（TASK K 的加载通道仍在）。
        self.assertIn("{% block extra_js %}", content)
