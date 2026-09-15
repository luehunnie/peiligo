"""B01 契约验证（ADR-0008）：API 响应形状逐字段对照 docs/api/openapi.json。

手写 JSON Schema 子集校验器（覆盖本契约实际使用的关键字：$ref/type/
required/properties/items/enum/const/minimum/minItems/maxItems/minLength/
oneOf/allOf），零新依赖。每个端点以构造内容打真实请求：200 响应对照
端点 schema，非 2xx 对照 Error 封装——响应形状与 B01 契约漂移即失败。

oneOf 按 OpenAPI 严格语义校验（恰一分支匹配）：五类详情 schema 的
type 判别常量已钉死（F04 校验修复），类型值另由本文件显式断言。
"""

import datetime as dt
import json
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from notices.models import NoticePage
from wagtail.models import Page

from .helpers import (
    _save,
    build_sections,
    future,
    make_article,
    make_container,
    make_department,
    make_guide,
    make_material,
    make_notice,
    make_software,
)

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "docs" / "api" / "openapi.json"
OPENAPI = json.loads(OPENAPI_PATH.read_text())
SCHEMAS = OPENAPI["components"]["schemas"]

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def resolve_ref(schema):
    while "$ref" in schema:
        schema = SCHEMAS[schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def assert_matches(value, schema, path="$"):
    """递归校验 value 是否匹配 schema（契约子集）；失败即 AssertionError。"""
    schema = resolve_ref(schema)
    if "allOf" in schema:
        for branch in schema["allOf"]:
            assert_matches(value, branch, path)
    if "oneOf" in schema:
        hits = sum(_matches(value, branch) for branch in schema["oneOf"])
        assert hits == 1, f"{path}: oneOf 匹配 {hits} 个分支（须恰一）"
        return
    type_spec = schema.get("type")
    if type_spec:
        types = type_spec if isinstance(type_spec, list) else [type_spec]
        assert any(_TYPE_CHECKS[t](value) for t in types), (
            f"{path}: 期望类型 {types}，实得 {type(value).__name__}（{value!r}）"
        )
    if "const" in schema:
        assert value == schema["const"], f"{path}: 期望常量 {schema['const']!r}，实得 {value!r}"
    if "enum" in schema:
        assert value in schema["enum"], f"{path}: {value!r} 不在枚举 {schema['enum']}"
    if isinstance(value, dict):
        for key in schema.get("required", []):
            assert key in value, f"{path}: 缺必填键 {key}"
        for key, branch in schema.get("properties", {}).items():
            if key in value:
                assert_matches(value[key], branch, f"{path}.{key}")
    if isinstance(value, list):
        if "minItems" in schema:
            assert len(value) >= schema["minItems"], f"{path}: {len(value)} < minItems"
        if "maxItems" in schema:
            assert len(value) <= schema["maxItems"], f"{path}: {len(value)} > maxItems"
        if "items" in schema:
            for index, item in enumerate(value):
                assert_matches(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, str) and "minLength" in schema:
        assert len(value) >= schema["minLength"], f"{path}: 短于 minLength"
    if "minimum" in schema and isinstance(value, (int, float)) and not isinstance(value, bool):
        assert value >= schema["minimum"], f"{path}: {value} < minimum {schema['minimum']}"


def _matches(value, schema):
    try:
        assert_matches(value, schema)
        return True
    except AssertionError:
        return False


def response_matches(response, schema_name):
    """响应 JSON 对照具名 schema（失败时携带响应体片段辅助定位）。"""
    data = response.json()
    try:
        assert_matches(data, {"$ref": f"#/components/schemas/{schema_name}"})
    except AssertionError as error:
        raise AssertionError(
            f"{schema_name} 契约漂移：{error}\n"
            f"响应体片段：{json.dumps(data, ensure_ascii=False)[:400]}"
        ) from error
    return data


def _body(*blocks):
    return json.loads(json.dumps(list(blocks)))


def _api_path(page):
    """页面具名 URL（/chronicle/contract-dept/contract-notice/）→ API 路径
    段（chronicle/contract-dept/contract-notice，E6 无尾斜杠形态）。"""
    return page.url.strip("/")


class ApiContractTestCase(TestCase):
    """公共内容面：五类内容页各一（含活动字段/到期），覆盖 E1–E8 全端点。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("契约测试处", "contract-dept")
        cls.chronicle = make_container(cls.sections["chronicle"], cls.department)
        cls.events = make_container(cls.sections["events"], cls.department)
        cls.materials = make_container(cls.sections["materials"], cls.department)
        cls.software = make_container(cls.sections["software"], cls.department)
        cls.guide = make_container(cls.sections["guide"], cls.department)
        cls.notice = make_notice(
            cls.chronicle, slug="contract-notice", title="契约通知", publish=True
        )
        # 活动字段（EventFieldsMixin）ORM 直建（clean 合法路径＝events 板块）。
        cls.event_notice = _save(
            NoticePage(
                title="契约活动",
                slug="contract-event",
                summary="测试摘要",
                department=cls.events.department,
                expire_at=future(),
                event_start_at=future(days=2),
                event_end_at=future(days=3),
                event_location="大礼堂",
                event_registration_url="https://forms.example.com/signup",
                body=_body({"type": "paragraph", "value": "<p>活动说明。</p>"}),
            ),
            cls.events,
            publish=True,
        )
        cls.article = make_article(
            cls.chronicle, slug="contract-article", title="契约文章", publish=True
        )
        cls.material = make_material(
            cls.materials, slug="contract-material", title="契约资料", publish=True
        )
        cls.software_tool = make_software(
            cls.software, slug="contract-software", title="契约工具", publish=True
        )
        cls.guide_page = make_guide(
            cls.guide, slug="contract-guide", title="契约指南", publish=True
        )

    def assert_method_not_allowed_contract(self, path):
        """非 GET 一律 405＋Error 封装＋Allow: GET（§2.1/§2.4）。"""
        for method in ("post", "put", "delete"):
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response["Allow"], "GET")
                response_matches(response, "Error")

    def test_e1_chrome_shape(self):
        response = self.client.get("/api/v1/chrome")
        self.assertEqual(response.status_code, 200)
        response_matches(response, "Chrome")

    def test_e2_home_shape(self):
        response = self.client.get("/api/v1/home")
        self.assertEqual(response.status_code, 200)
        data = response_matches(response, "Home")
        self.assertEqual(data["title"], "首页")

    def test_e3_section_list_shape(self):
        response = self.client.get("/api/v1/sections/chronicle")
        self.assertEqual(response.status_code, 200)
        data = response_matches(response, "SectionList")
        self.assertEqual(data["section"]["slug"], "chronicle")

    def test_e3_section_list_shape_filtered(self):
        response = self.client.get("/api/v1/sections/chronicle?type=notice&q=契约")
        self.assertEqual(response.status_code, 200)
        response_matches(response, "SectionList")

    def test_e4_archive_shape(self):
        response = self.client.get("/api/v1/sections/chronicle/archive")
        self.assertEqual(response.status_code, 200)
        data = response_matches(response, "SectionArchive")
        self.assertEqual(data["total"], 2)

    def test_e5_search_shape(self):
        response = self.client.get("/api/v1/search?q=契约&type=notice")
        self.assertEqual(response.status_code, 200)
        data = response_matches(response, "SearchResults")
        self.assertEqual(data["q"], "契约")
        self.assertEqual(len(data["chips"]), 6)

    def test_e6_detail_shapes_five_types(self):
        """五类详情各对照其具名 schema；type 判别值一一对应。"""
        cases = (
            (self.notice, "NoticeDetail", "notice"),
            (self.event_notice, "NoticeDetail", "notice"),
            (self.article, "ArticleDetail", "article"),
            (self.material, "MaterialDetail", "material"),
            (self.software_tool, "SoftwareToolDetail", "software"),
            (self.guide_page, "GuideDetail", "guide"),
        )
        for page, schema_name, type_value in cases:
            with self.subTest(type=type_value):
                response = self.client.get(f"/api/v1/pages/{_api_path(page)}")
                self.assertEqual(response.status_code, 200)
                data = response_matches(response, schema_name)
                self.assertEqual(data["type"], type_value)

    def test_e6_expired_detail_shape(self):
        """expired 放行详情仍是 NoticeDetail 形状（expired 标记如实填充）。"""
        notice = make_notice(self.chronicle, slug="contract-expired", publish=True)
        Page.objects.filter(pk=notice.pk).update(
            expire_at=timezone.now() - dt.timedelta(hours=1)
        )
        call_command("publish_scheduled", verbosity=0)
        notice.refresh_from_db()
        response = self.client.get(f"/api/v1/pages/{_api_path(notice)}")
        self.assertEqual(response.status_code, 200)
        data = response_matches(response, "NoticeDetail")
        self.assertTrue(data["expired"])

    def test_e7_link_confirm_shape_ok_and_reject(self):
        ok = self.client.get("/api/v1/link-confirm", {"url": "https://example.com/doc"})
        self.assertEqual(ok.status_code, 200)
        response_matches(ok, "LinkConfirm")
        bad = self.client.get("/api/v1/link-confirm", {"url": "javascript:alert(1)"})
        self.assertEqual(bad.status_code, 200)
        data = response_matches(bad, "LinkConfirm")
        self.assertFalse(data["ok"])

    def test_e8_sitemap_shape(self):
        response = self.client.get("/api/v1/sitemap")
        self.assertEqual(response.status_code, 200)
        response_matches(response, "Sitemap")

    def test_error_envelopes_match_contract(self):
        """404 封装对照 Error schema；code 枚举在封装内。"""
        response = self.client.get("/api/v1/pages/chronicle/contract-dept/missing")
        self.assertEqual(response.status_code, 404)
        data = response_matches(response, "Error")
        self.assertEqual(data["error"]["code"], "not_found")

    def test_e6_union_strict_exactly_one_branch(self):
        """F04 回归：E6 判别联合对真实响应必须恰一分支可匹配——type 判别
        常量钉死前，notice/article 两分支形状同构，任一有效负载双匹配，
        严格 OpenAPI 校验恒败。"""
        cases = (
            (self.notice, "NoticeDetail"),
            (self.event_notice, "NoticeDetail"),
            (self.article, "ArticleDetail"),
            (self.material, "MaterialDetail"),
            (self.software_tool, "SoftwareToolDetail"),
            (self.guide_page, "GuideDetail"),
        )
        for page, expected in cases:
            with self.subTest(expected=expected):
                response = self.client.get(f"/api/v1/pages/{_api_path(page)}")
                self.assertEqual(response.status_code, 200)
                data = response.json()
                hits = [
                    name
                    for name in (
                        "NoticeDetail",
                        "ArticleDetail",
                        "MaterialDetail",
                        "SoftwareToolDetail",
                        "GuideDetail",
                    )
                    if _matches(data, {"$ref": f"#/components/schemas/{name}"})
                ]
                self.assertEqual(hits, [expected])

    def test_all_endpoints_get_only(self):
        self.assert_method_not_allowed_contract("/api/v1/chrome")
        self.assert_method_not_allowed_contract("/api/v1/home")
        self.assert_method_not_allowed_contract("/api/v1/sections/chronicle")
        self.assert_method_not_allowed_contract("/api/v1/sections/chronicle/archive")
        self.assert_method_not_allowed_contract("/api/v1/search")
        self.assert_method_not_allowed_contract("/api/v1/link-confirm")
        self.assert_method_not_allowed_contract("/api/v1/sitemap")
        self.assert_method_not_allowed_contract("/api/v1/preview")
