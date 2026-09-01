"""F-01 E1 生产接线回归（ADR-0006）：显式后端选择＋icontains 语义锁定。

三层断言（批令 §8：只做功能测试；200/1000/5000 性能复验＝VALIDATION_ONLY）：

1. 装配事实——settings ``default`` 后端＝项目内 E1 子类（fallback 实现），
   经 ``get_search_backend`` 取得实例即 E1；任何 vendor 下不再发生 vendor
   分派（ADR-0006 PRODUCTION_IMPLEMENTATION_REQUIRED=YES 的接线义务）。
2. 反事实守门——通用 database 后端在本连接（生产同 vendor：PostgreSQL）
   仍会分派到 FTS 后端：证明「不显式选择＝E2 语义」，接线缺失即全站
   搜索语义静默漂移（audit §8 HIGH-1）。
3. 语义锁定——经 /search/ 入口的子串命中（标题词中片段／2 字短词／正文
   子串）：PG FTS（simple，CJK 连续串整串单 token）下必失分，E1
   icontains 下必命中；另含无结果 200 空集语义。
"""

import json
import unittest

from django.conf import settings
from django.db import connection
from notices.models import NoticePage
from search.backends import E1IcontainsSearchBackend
from wagtail.search.backends import get_search_backend
from wagtail.search.backends.database import SearchBackend as VendorDispatchBackend
from wagtail.search.backends.database.fallback import DatabaseSearchBackend
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import (
    _save,
    build_sections,
    future,
    make_container,
    make_department,
    make_notice,
)


class E1WiringTests(WagtailPageTestCase):
    """装配事实与反事实守门（不依赖数据）。"""

    def test_settings_select_e1_backend(self):
        backend_path = settings.WAGTAILSEARCH_BACKENDS["default"]["BACKEND"]
        self.assertEqual(backend_path, "search.backends.E1IcontainsSearchBackend")

    def test_default_backend_instance_is_e1_fallback(self):
        backend = get_search_backend("default")
        self.assertIsInstance(backend, E1IcontainsSearchBackend)
        self.assertIsInstance(backend, DatabaseSearchBackend)

    @unittest.skipUnless(connection.vendor == "postgresql", "反事实仅在 PG vendor 下成立")
    def test_vendor_dispatch_would_be_fts_without_explicit_selection(self):
        """通用 database 后端在 PG 上分派到 FTS＝E2 语义（仅验分派事实，
        不执行其查询——即 E1 必须显式选择的原因）。"""
        dispatched = VendorDispatchBackend({})
        self.assertNotIsInstance(dispatched, E1IcontainsSearchBackend)
        self.assertEqual(type(dispatched).__name__, "PostgresSearchBackend")


class E1IcontainsSemanticsTests(WagtailPageTestCase):
    """经 /search/ 入口的 icontains 子串语义锁定（生产同 vendor：PG）。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.jwc = make_department("教务处", "jwc")
        cls.cwc = make_department("财务处", "cwc")
        cls.container = make_container(cls.sections["chronicle"], cls.jwc)
        cls.cwc_container = make_container(cls.sections["chronicle"], cls.cwc)
        # 标题词中片段／2 字短词探针：查询串为标题的中间子串，非整串。
        cls.title_probe = make_notice(
            cls.container,
            slug="e1-title",
            title="全国大学生数学建模竞赛报名通知",
            publish=True,
        )
        # 正文子串探针：标题不含查询串、正文含（金标 Q03 同口径）。
        cls.body_probe = _save(
            NoticePage(
                title="关于调整差旅费标准的通知",
                slug="e1-body",
                summary="测试摘要",
                department=cls.cwc_container.department,
                expire_at=future(),
                body=json.loads(
                    json.dumps([{"type": "paragraph", "value": "<p>差旅费报销标准调整如下。</p>"}])
                ),
            ),
            cls.cwc_container,
            publish=True,
        )

    def _hit(self, query):
        response = self.client.get("/search/", {"q": query})
        self.assertEqual(response.status_code, 200)
        return {page.pk for page in response.context["search_results"]}

    def test_title_midstring_and_two_char_fragment(self):
        """词中片段（4 字／3 字）与 2 字短词均命中——PG FTS 整串单 token 下必失分。"""
        for query in ("数学建模", "建模", "赛报名"):
            with self.subTest(fragment=query):
                self.assertIn(self.title_probe.pk, self._hit(query))

    def test_body_substring_hit_with_title_miss_scope(self):
        """正文子串命中；标题不含该串的页面不因标题误命中。"""
        self.assertIn(self.body_probe.pk, self._hit("报销"))
        self.assertNotIn(self.title_probe.pk, self._hit("报销"))

    def test_no_result_is_200_empty(self):
        """无结果查询＝200＋空集（§21.3 口径，不 404/不 5xx）。"""
        response = self.client.get("/search/", {"q": "量子计算机采购招标"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["search_results"]), [])
