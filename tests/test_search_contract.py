"""M3.4 搜索契约行为测试（CONTENT_MODEL §21；批令 §18 清单）。

断言面：§21 筛选四维＋组合＋非法值视同未提供（200 回退全量）；§21.5
可见性四排除＋Expired（CURRENT_DEFAULT 同谓词 live∧¬expired）；IA §9
URL 全 GET 可分享；IA §10 收录（noindex/去参 canonical/§8.2 筛选态标题）。
中文检索只测契约（整 token 命中——E2 simple 语义下 CJK 连续串成单
token），不虚构分词质量。词表 M2M 名文本依赖 update_index 批量重建
（发布期即时索引不捕捉 cluster M2M 变更——上游时机限制，登记见 impl
报告），故建数据后统一重建再断言。search_fields 逐页反射与契约常量
断言见 tests/test_search_fields_reflection.py。
"""

import json
from io import StringIO

from django.core.management import call_command
from notices.models import NoticePage, Tag
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import (
    _save,
    body_json,
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
from tests.test_current_default import expire_page


class SearchContractTestCase(WagtailPageTestCase):
    """公共数据：五板块×两部门×五类内容各一＋活动通知＋受控标签。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.jwc = make_department("教务处", "jwc")
        cls.xsc = make_department("学生处", "xsc")
        c_chr = make_container(cls.sections["chronicle"], cls.jwc)
        c_eve = make_container(cls.sections["events"], cls.jwc)
        c_mat = make_container(cls.sections["materials"], cls.jwc)
        c_sof = make_container(cls.sections["software"], cls.xsc)
        c_gui = make_container(cls.sections["guide"], cls.xsc)
        cls.notice = make_notice(c_chr, slug="n1", title="开学典礼通知", publish=True)
        # 活动板块通知：EventFieldsMixin clean 强制活动字段（§7.2 板块决定），
        # 须随建随填（活动地点＝§20.1 表 B 低权检索目标）。
        cls.event_notice = _save(
            NoticePage(
                title="迎新晚会通知",
                slug="n2",
                summary="测试摘要",
                department=c_eve.department,
                expire_at=future(),
                body=json.loads(body_json()),
                event_start_at=future(days=3),
                event_end_at=future(days=4),
                event_location="大学生活动中心",
            ),
            c_eve,
            publish=True,
        )
        cls.article = make_article(c_chr, slug="a1", title="社团招新文章", publish=True)
        cls.material = make_material(c_mat, slug="m1", title="高等数学课件", publish=True)
        cls.software = make_software(c_sof, slug="s1", title="设计软件工具", publish=True)
        cls.guide = make_guide(c_gui, slug="g1", title="食堂就餐指南", publish=True)
        cls.notice.tags.set([Tag.objects.create(name="开学季", slug="kaixue")])
        cls.notice.save_revision().publish()
        call_command("update_index", stdout=StringIO())

    def _pks(self, path, params=None):
        response = self.client.get(path, params or {})
        self.assertEqual(response.status_code, 200)
        key = "search_results" if path == "/search/" else "content_entries"
        return {page.pk for page in response.context[key]}


class QueryHitsTests(SearchContractTestCase):
    """PRD §10 覆盖面：七类查询目标整 token 命中（契约级，非质量宣称）。"""

    def test_query_hits_declared_fields(self):
        hits = [
            ("标题", "开学典礼通知", self.notice),
            ("正文", "测试正文段落", self.notice),
            ("部门名", "教务处", self.notice),
            ("受控标签名", "开学季", self.notice),
            ("学科词表名", "计算机科学", self.material),
            ("指南地点", "第一教学楼一层", self.guide),
            ("指南开放时间", "工作日", self.guide),
            ("活动地点", "大学生活动中心", self.event_notice),
        ]
        for label, query, target in hits:
            with self.subTest(hit=label):
                self.assertIn(target.pk, self._pks("/search/", {"q": query}))

    def test_empty_q_is_pure_orm_no_backend_call(self):
        """§21.1：空串/空白 q＝不加条件；无任何有效参数＝表单态不查全量。"""
        self.assertEqual(self._pks("/search/", {"q": " "}), set())
        self.assertFalse(self.client.get("/search/").context["filter_active"])


class FilterDimensionTests(SearchContractTestCase):
    """§21.1 四维＋组合与 URL 状态；§21.2 tag 双通道与词表通道。"""

    def test_section_filter_scopes_path_range(self):
        self.assertEqual(
            self._pks("/search/", {"section": "chronicle"}), {self.notice.pk, self.article.pk}
        )

    def test_dept_filter(self):
        self.assertEqual(self._pks("/search/", {"dept": "xsc"}), {self.software.pk, self.guide.pk})

    def test_type_filter(self):
        self.assertEqual(self._pks("/search/", {"type": "material"}), {self.material.pk})

    def test_tag_slug_and_name_channels_and_vocab(self):
        self.assertEqual(self._pks("/search/", {"tag": "kaixue"}), {self.notice.pk})
        self.assertEqual(self._pks("/search/", {"tag": "开学季"}), {self.notice.pk})
        self.assertEqual(self._pks("/search/", {"tag": "计算机科学"}), {self.material.pk})

    def test_combined_filters(self):
        self.assertEqual(
            self._pks("/search/", {"section": "chronicle", "dept": "jwc", "type": "notice"}),
            {self.notice.pk},
        )
        # 组合含检索词：filter-first 下检索仍与其他维度合取（§21.6）。
        self.assertEqual(
            self._pks("/search/", {"q": "开学典礼通知", "dept": "jwc", "type": "notice"}),
            {self.notice.pk},
        )

    def test_invalid_values_fall_back_to_unfiltered(self):
        """§21.3：非法值视同未提供（200 回退全量，非 404/非 5xx）。"""
        baseline = self._pks("/search/", {"q": "开学典礼通知"})
        fallen = self._pks(
            "/search/",
            {"q": "开学典礼通知", "section": "bogus", "dept": "nope", "type": "wat", "tag": "zzz"},
        )
        self.assertEqual(baseline, fallen)

    def test_section_page_ignores_section_param(self):
        """§21.1：板块页 ?section= 一律忽略（板块维度由路径唯一决定）。"""
        self.assertEqual(self._pks("/chronicle/", {"section": "guide"}), self._pks("/chronicle/"))

    def test_section_page_filter_and_no_match_state(self):
        self.assertEqual(self._pks("/chronicle/", {"type": "notice"}), {self.notice.pk})
        response = self.client.get("/chronicle/", {"dept": "xsc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["content_entries"]), [])
        self.assertContains(response, "没有符合当前条件的内容")

    def test_get_state_reproducible_and_links_to_detail(self):
        """IA §9.2 #3：状态全在 URL（GET 可分享/可刷新/可复原）。"""
        params = {"q": "开学典礼通知", "dept": "jwc", "type": "notice"}
        first, second = (self.client.get("/search/", params) for _ in range(2))
        self.assertEqual(
            [p.pk for p in first.context["search_results"]],
            [p.pk for p in second.context["search_results"]],
        )
        self.assertContains(first, self.notice.url)


class VisibilityTests(SearchContractTestCase):
    """§21.5/PS-33：CURRENT_DEFAULT＝§16.4 同谓词 live∧¬expired。"""

    def test_four_exclusions_and_expired(self):
        from tests.helpers import future

        container = self.notice.get_parent().specific
        draft = make_notice(container, slug="v-draft", title="草稿态通知", publish=False)
        scheduled = make_notice(container, slug="v-sched", title="预约态通知", schedule_at=future())
        unpublished = make_notice(container, slug="v-unpub", title="已下线通知", publish=True)
        unpublished.unpublish()
        expired = make_notice(container, slug="v-exp", title="已到期通知", publish=True)
        expire_page(expired)
        for page in (draft, scheduled, unpublished, expired):
            with self.subTest(state=page.slug):
                self.assertEqual(self._pks("/search/", {"q": page.title}), set())
                self.assertNotIn(page.pk, self._pks("/chronicle/"))
        self.assertIn(self.notice.pk, self._pks("/chronicle/"))


class SeoTests(SearchContractTestCase):
    """IA §10 #6/#7＋§8.2：noindex/去参 canonical/筛选态标题/禁门户措辞。"""

    def test_search_page_noindex_all_states(self):
        for params in ({}, {"q": "开学典礼通知"}, {"dept": "jwc"}):
            with self.subTest(params=params):
                response = self.client.get("/search/", params)
                self.assertContains(response, '<meta name="robots" content="noindex">')
                self.assertContains(response, 'rel="canonical" href="http://testserver/search/"')

    def test_section_page_indexability_by_state(self):
        base = self.client.get("/chronicle/")
        self.assertNotContains(base, "noindex")
        filtered = self.client.get("/chronicle/", {"dept": "jwc"})
        self.assertContains(filtered, '<meta name="robots" content="noindex">')
        self.assertContains(filtered, 'rel="canonical" href="http://testserver/chronicle/"')

    def test_dept_filtered_title_pattern(self):
        """§8.2：dept 筛选态 H1 与 <title> 同文案（含"（筛选结果）"后缀）。"""
        pattern = "校园纪事·教务处发布的内容（筛选结果）"
        response = self.client.get("/chronicle/", {"dept": "jwc"})
        self.assertEqual(response.content.decode().count(pattern), 2)
        for wording in ("部门主页", "部门门户", "部门空间", "部门专区"):
            self.assertNotContains(response, wording)
