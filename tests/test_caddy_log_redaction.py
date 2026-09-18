"""SPEC-001 · 预览票据不落 Caddy 访问日志（配置守护）。

契约「票据不落访问日志」的 Caddy 侧闭合：deploy/Caddyfile 的 log 块经
内置 filter 编码器（caddy.logging.encoders.filter，caddy:2 主线自带——
零插件、零换镜像）只在日志面抹除票据，请求面零改动（路由表、上游、
token 语义均不动）。本守护把配置形态钉进 CI 门（pytest 即跑）：

- filter 编码器必须 wrap json（与缺省 json 编码同形状，仅差票据抹除；
  路径/状态/耗时字段照常），``output stdout`` 仍在（不做关日志）；
- request>uri 必须是 query 过滤器 ``delete token``——删除参数而非关整条
  查询串，普通查询参数照常记录；
- request>headers>Referer 必须是内联位置形态的 regexp 过滤器。该过滤器的
  两个参数是位置形式，写成子块会被 Caddy **静默忽略**（validate 也不报
  错，实测于 caddy:2.11.4），故按逐字符形态钉住，漂移即红；
- compose 侧 caddy 仍为 caddy:2 且挂载 ./Caddyfile（机制可用性的前提面）。

行为级哨兵实测（一次性集成栈：哨兵票据请求 → caddy 日志零哨兵、普通
路径/查询/状态/耗时日志健在）见 deploy/verify-preview-log-redaction.sh，
runbook §12 残余风险备忘已随之闭合。
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"

# regexp 过滤器的唯一合法（内联位置）形态——子块等错误写法会被 Caddy
# 静默忽略成「不过滤」，这是本守护存在的核心理由。
REFERER_FILTER_LINE = 'request>headers>Referer regexp "token=[^&]+" "token=REDACTED"'


class CaddyAccessLogRedactionGuard(SimpleTestCase):
    """deploy/Caddyfile 访问日志票据抹除配置，逐项钉住防漂移。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.caddyfile = (DEPLOY / "Caddyfile").read_text(encoding="utf-8")
        # log 块作用域：从 site 内 ``log {`` 到其收口（一层缩进 ``}``）。
        m = re.search(r"^\tlog \{.*?^\t\}", cls.caddyfile, re.S | re.M)
        assert m, "deploy/Caddyfile 缺 site 级 log 块"
        cls.log_block = m.group(0)

    def test_filter_encoder_wraps_json_and_keeps_stdout(self):
        """filter 编码器在位、包 json（同形状只差抹除）、stdout 仍在。"""
        self.assertIn("format filter {", self.log_block)
        self.assertIn("wrap json", self.log_block)
        self.assertIn("output stdout", self.log_block)

    def test_uri_query_filter_deletes_token_param_only(self):
        """request>uri：query 过滤器 delete token（参数级删除，非关日志）。"""
        self.assertIn("request>uri query {", self.log_block)
        self.assertIn("delete token", self.log_block)

    def test_referer_regexp_filter_exact_inline_form(self):
        """request>headers>Referer：regexp 过滤器必须是内联位置形态——

        子块/改名等漂移会被 Caddy 静默忽略（validate 照样过），日志里
        票据照落，唯一防线就是这里逐字符钉住。"""
        self.assertIn(REFERER_FILTER_LINE, self.log_block)

    def test_logging_not_disabled(self):
        """不做关日志（log off / discard 输出均视为回归）。"""
        self.assertNotIn("log off", self.caddyfile)
        self.assertNotIn("output discard", self.caddyfile)

    def test_compose_still_mounts_caddyfile_on_caddy_2(self):
        """机制前提面：compose 仍以 caddy:2 跑 ./Caddyfile。"""
        compose = (DEPLOY / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertRegex(compose, r"(?m)^\s+image: caddy:2\s*$")
        self.assertIn("./Caddyfile:/etc/caddy/Caddyfile:ro", compose)
