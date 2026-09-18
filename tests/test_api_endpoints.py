"""API v1 端点语义（E1–E8）：与现有 Django 模板渲染行为等价的断言面。

可见性谓词（CURRENT_DEFAULT/HISTORICAL/详情放行）、搜索语义（非法值视
同未提供、表单态短路、宽容分页、chips）、外链确认门、轮播/快讯组稿、
sitemap 排除与新鲜度（每请求实时计算）——均以既有权威实现为唯一口径
（notices/lifecycle.py、search/services.py、home/models.py、home/views.py），
本文件锁定 API 投影不漂移。
"""

import datetime as dt
import json
from urllib.parse import quote

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from home.models import CarouselItem, SiteSettings
from notices.models import NoticePage
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Page, Site

from .helpers import (
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
    past,
)


def _body(*blocks):
    return json.loads(json.dumps(list(blocks)))


def expire(page):
    """E7 到期（既有测试同款：置过去 expire_at ＋ 调度器单周期）。"""
    Page.objects.filter(pk=page.pk).update(expire_at=timezone.now() - dt.timedelta(hours=1))
    call_command("publish_scheduled", verbosity=0)
    page.refresh_from_db()


def _path(page):
    """页面具名 URL → API 路径段（E6 无尾斜杠形态）。"""
    return page.url.strip("/")


def make_inline_image(title="测试图片"):
    """请求期可再读的源图（helpers.make_image 的临时目录即建即清，不适合
    需要在请求中二次生成 rendition 的场景；文件落测试 MEDIA_ROOT）。"""
    import io

    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (1200, 800), (200, 60, 60)).save(buf, format="PNG")
    image = Image(title=title)
    image.file = SimpleUploadedFile("inline.png", buf.getvalue(), content_type="image/png")
    image.save()
    return image


class EndpointDataTestCase(TestCase):
    """公共数据：五板块＋两部门容器＋基础内容。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.jwc = make_department("教务处", "jwc")
        cls.xgb = make_department("学生处", "xgb")
        cls.jwc_chronicle = make_container(cls.sections["chronicle"], cls.jwc)
        cls.xgb_chronicle = make_container(cls.sections["chronicle"], cls.xgb)
        cls.jwc_events = make_container(cls.sections["events"], cls.jwc)
        cls.notice = make_notice(
            cls.jwc_chronicle, slug="ep-notice", title="端点通知", publish=True
        )
        cls.article = make_article(
            cls.xgb_chronicle, slug="ep-article", title="端点文章", publish=True
        )


class ChromeEndpointTests(EndpointDataTestCase):
    def test_frozen_nav_order_and_paths(self):
        data = self.client.get("/api/v1/chrome").json()
        self.assertEqual(data["site_name"], "Peiligo")
        self.assertEqual(
            [(item["slug"], item["title"], item["url"]) for item in data["nav_sections"]],
            [
                ("chronicle", "校园纪事", "/chronicle/"),
                ("events", "校园活动", "/events/"),
                ("materials", "学习资料", "/materials/"),
                ("software", "软件与工具", "/software/"),
                ("guide", "校园指南", "/guide/"),
            ],
        )

    def test_feedback_email_present(self):
        data = self.client.get("/api/v1/chrome").json()
        self.assertTrue(data["feedback_email"])

    def test_alert_window_reflects_next_request(self):
        """F4：紧急提示每请求实时计算——设置后下一请求出现，清空即消失。"""
        site = Site.objects.get(is_default_site=True)
        settings_obj = SiteSettings.for_site(site)
        settings_obj.alert_text = "临时管制通知"
        settings_obj.save()
        self.assertEqual(
            self.client.get("/api/v1/chrome").json()["alert"],
            {"text": "临时管制通知"},
        )
        settings_obj.alert_text = "  "
        settings_obj.save()
        self.assertIsNone(self.client.get("/api/v1/chrome").json()["alert"])

    def test_alert_window_boundary(self):
        """成对窗口须 起 ≤ now ≤ 止（_active_alert 唯一口径）。"""
        site = Site.objects.get(is_default_site=True)
        settings_obj = SiteSettings.for_site(site)
        settings_obj.alert_text = "窗口提示"
        settings_obj.alert_start_at = past(days=1)
        settings_obj.alert_end_at = future(days=1)
        settings_obj.save()
        self.assertEqual(self.client.get("/api/v1/chrome").json()["alert"], {"text": "窗口提示"})
        settings_obj.alert_end_at = timezone.now() - dt.timedelta(minutes=1)
        settings_obj.save()
        self.assertIsNone(self.client.get("/api/v1/chrome").json()["alert"])


class HomeEndpointTests(EndpointDataTestCase):
    def test_sections_live_only_in_frozen_order(self):
        data = self.client.get("/api/v1/home").json()
        self.assertEqual(
            [s["slug"] for s in data["sections"]],
            ["chronicle", "events", "materials", "software", "guide"],
        )

    def test_campus_news_cap_dedup_and_ended_skip(self):
        """组稿规则（Phase 8C）：至多 3 条、同页去重、已结束活动不入轨。"""
        for index in range(4):
            make_notice(
                self.jwc_chronicle,
                slug=f"news-{index}",
                title=f"快讯{index}",
                publish=True,
            )
        ended = _save(
            NoticePage(
                title="已结束活动",
                slug="ended-event",
                summary="测试摘要",
                department=self.jwc_events.department,
                expire_at=future(),
                event_start_at=past(days=3),
                event_end_at=past(days=1),
                event_location="旧体育馆",
                body=json.loads(body_json()),
            ),
            self.jwc_events,
            publish=True,
        )
        data = self.client.get("/api/v1/home").json()
        titles = [entry["title"] for entry in data["campus_news"]]
        self.assertEqual(len(titles), 3)
        self.assertNotIn("已结束活动", titles)
        self.assertEqual(len({entry["id"] for entry in data["campus_news"]}), 3)
        self.assertIsNotNone(ended)

    def test_campus_news_entry_fields(self):
        data = self.client.get("/api/v1/home").json()
        entry = next(e for e in data["campus_news"] if e["id"] == self.notice.pk)
        self.assertEqual(entry["type"], "notice")
        self.assertEqual(entry["href"], self.notice.url)
        self.assertEqual(entry["section_slug"], "chronicle")
        self.assertEqual(entry["department"], "教务处")
        self.assertIsNone(entry["cover"])
        self.assertEqual(entry["summary"], "测试摘要")

    def test_carousel_external_entry_confirm_href(self):
        """轮播外链项＝确认链（无裸外链）；站内项＝目标页具名 URL。"""
        CarouselItem.objects.create(
            external_title="外部资源", external_url="https://files.example.com/setup"
        )
        CarouselItem.objects.create(internal_page=self.notice)
        data = self.client.get("/api/v1/home").json()
        by_title = {entry["title"]: entry for entry in data["carousel"]}
        external = by_title["外部资源"]
        self.assertEqual(external["kind"], "external")
        self.assertEqual(external["summary"], "")
        self.assertIn("/link-confirm/?url=", external["href"])
        self.assertIn(quote("https://files.example.com/setup", safe="/"), external["href"])
        internal = by_title["端点通知"]
        self.assertEqual(internal["kind"], "internal")
        self.assertEqual(internal["href"], self.notice.url)
        self.assertEqual(internal["section_slug"], "chronicle")


class SectionListEndpointTests(EndpointDataTestCase):
    def _list(self, section_slug, query=None):
        response = self.client.get(f"/api/v1/sections/{section_slug}", query or {})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_current_default_predicate(self):
        """E3＝CURRENT_DEFAULT：draft/scheduled/expired 一律不入。"""
        make_notice(self.jwc_chronicle, slug="draft-hidden", title="草稿通知")
        make_notice(self.jwc_chronicle, slug="live-shown", title="在线通知", publish=True)
        expired = make_notice(
            self.jwc_chronicle, slug="expired-hidden", title="到期通知", publish=True
        )
        expire(expired)
        slugs = [entry["title"] for entry in self._list("chronicle")["entries"]]
        self.assertIn("在线通知", slugs)
        self.assertNotIn("草稿通知", slugs)
        self.assertNotIn("到期通知", slugs)

    def test_path_section_param_ignored(self):
        """/sections/{slug} 不读 ?section=（路径唯一锚定，回显恒 null）。"""
        data = self.client.get("/api/v1/sections/chronicle?section=events").json()
        self.assertIsNone(data["filters"]["section"])
        self.assertFalse(data["filters"]["active"])

    def test_illegal_values_treated_as_absent(self):
        """§21.3：非法值 200 回退全量，不 400 不 404；回显对应 null。"""
        data = self.client.get(
            "/api/v1/sections/chronicle?type=bogus&dept=nobody&tag=词表外&q=  "
        ).json()
        self.assertIsNone(data["filters"]["type"])
        self.assertIsNone(data["filters"]["dept"])
        self.assertIsNone(data["filters"]["tag"])
        self.assertEqual(data["filters"]["q"], "")
        self.assertFalse(data["filters"]["active"])
        self.assertTrue(data["pagination"]["total"] >= 1)

    def test_filters_narrow_results_and_echo(self):
        data = self._list("chronicle", {"dept": "jwc", "type": "notice"})
        self.assertEqual([e["title"] for e in data["entries"]], ["端点通知"])
        echo = data["filters"]
        self.assertEqual(echo["dept"], "jwc")
        self.assertEqual(echo["type"], "notice")
        self.assertTrue(echo["active"])
        # 板块维度路径锚定仍入 conditions（active_conditions 唯一口径）。
        self.assertEqual(
            {(c["label"], c["value"]) for c in echo["conditions"]},
            {("板块", "校园纪事"), ("部门", "教务处"), ("内容类型", "通知页")},
        )

    def test_pagination_lenient_and_per_page_20(self):
        for index in range(22):
            make_notice(
                self.jwc_chronicle,
                slug=f"page-{index}",
                title=f"分页{index}",
                publish=True,
            )
        first = self._list("chronicle", {"page": "abc"})
        self.assertEqual(first["pagination"]["page"], 1)
        self.assertEqual(first["pagination"]["per_page"], 20)
        self.assertEqual(len(first["entries"]), 20)
        second = self._list("chronicle", {"page": "999"})
        self.assertEqual(second["pagination"]["page"], 2)
        # 基线两条（端点通知/端点文章）＋新增 22 条＝24 条 → 20＋4。
        self.assertEqual(len(second["entries"]), 4)
        self.assertEqual(second["pagination"]["page_count"], 2)
        self.assertTrue(first["pagination"]["has_next"])
        self.assertFalse(first["pagination"]["has_previous"])
        self.assertTrue(second["pagination"]["has_previous"])

    def test_list_entry_shape_values(self):
        entry = self._list("chronicle")["entries"][0]
        self.assertIn(entry["type"], ("notice", "article"))
        self.assertFalse(entry["expired"])
        self.assertEqual(entry["section_slug"], "chronicle")
        self.assertEqual(entry["section_title"], "校园纪事")
        self.assertIn(entry["department_name"], ("教务处", "学生处"))
        self.assertIsNotNone(entry["published_at"])
        self.assertEqual(entry["list_summary"], "测试摘要")

    def test_unknown_section_404_envelope(self):
        response = self.client.get("/api/v1/sections/bogus")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_freshness_publish_immediately_visible(self):
        """F2：发布即刻可见——两次请求间无缓存陈旧窗口。"""
        before = [e["title"] for e in self._list("chronicle")["entries"]]
        self.assertNotIn("新鲜通知", before)
        make_notice(self.jwc_chronicle, slug="fresh-notice", title="新鲜通知", publish=True)
        after = [e["title"] for e in self._list("chronicle")["entries"]]
        self.assertIn("新鲜通知", after)


class ArchiveEndpointTests(EndpointDataTestCase):
    def _archive(self, section="chronicle", query=None):
        return self.client.get(f"/api/v1/sections/{section}/archive", query or {}).json()

    def test_historical_full_no_pagination(self):
        """E4＝HISTORICAL 全量：expired 入列（带标记），无分页键。"""
        expired = make_notice(
            self.jwc_chronicle, slug="arch-expired", title="归档到期", publish=True
        )
        expire(expired)
        data = self._archive()
        titles = [entry["title"] for entry in data["entries"]]
        self.assertIn("归档到期", titles)
        self.assertIn("端点通知", titles)
        self.assertEqual(data["total"], len(data["entries"]))
        self.assertNotIn("pagination", data)
        expired_entry = next(e for e in data["entries"] if e["title"] == "归档到期")
        self.assertTrue(expired_entry["expired"])

    def test_query_params_have_no_effect(self):
        """归档非 §21 载体：查询参数零效果（全量不变）。"""
        plain = self._archive()
        filtered = self._archive(query={"type": "article", "dept": "xgb"})
        self.assertEqual(plain["total"], filtered["total"])
        self.assertEqual(
            [e["id"] for e in plain["entries"]], [e["id"] for e in filtered["entries"]]
        )

    def test_draft_never_in_archive(self):
        make_notice(self.jwc_chronicle, slug="arch-draft", title="归档草稿")
        titles = [e["title"] for e in self._archive()["entries"]]
        self.assertNotIn("归档草稿", titles)

    def test_unknown_section_404(self):
        self.assertEqual(self.client.get("/api/v1/sections/bogus/archive").status_code, 404)


class SearchEndpointTests(EndpointDataTestCase):
    def test_form_state_short_circuit(self):
        """无有效筛选维度＝表单态：零查询零结果（IA §9.2 #1 现状同构）。"""
        data = self.client.get("/api/v1/search").json()
        self.assertEqual(data["entries"], [])
        self.assertFalse(data["filters"]["active"])
        self.assertEqual(data["q"], "")
        self.assertEqual(data["chips"][0]["label"], "全部")

    def test_q_hits_and_stripped_echo(self):
        data = self.client.get("/api/v1/search?q=  端点通知  ").json()
        self.assertEqual(data["q"], "端点通知")
        self.assertEqual([e["title"] for e in data["entries"]], ["端点通知"])

    def test_historical_visibility(self):
        """E5＝HISTORICAL：expired 默认命中且带标记；草稿永不出。"""
        expired = make_notice(self.jwc_chronicle, slug="s-expired", title="搜索到期", publish=True)
        make_notice(self.jwc_chronicle, slug="s-draft", title="搜索草稿")
        expire(expired)
        data = self.client.get("/api/v1/search?q=搜索").json()
        titles = [e["title"] for e in data["entries"]]
        self.assertIn("搜索到期", titles)
        self.assertNotIn("搜索草稿", titles)
        expired_entry = next(e for e in data["entries"] if e["title"] == "搜索到期")
        self.assertTrue(expired_entry["expired"])

    def test_merged_order_by_first_published_desc(self):
        make_notice(self.jwc_chronicle, slug="s-newer", title="较新通知", publish=True)
        titles = [e["title"] for e in self.client.get("/api/v1/search?dept=jwc").json()["entries"]]
        self.assertLess(titles.index("较新通知"), titles.index("端点通知"))

    def test_chips_six_all_first_preserved_params_active_flag(self):
        data = self.client.get("/api/v1/search?q=x&section=events").json()
        chips = data["chips"]
        self.assertEqual(
            [c["slug"] for c in chips],
            ["", "chronicle", "events", "materials", "software", "guide"],
        )
        self.assertEqual(chips[0]["label"], "全部")
        self.assertTrue(chips[2]["active"])
        self.assertFalse(chips[0]["active"])
        self.assertFalse(chips[1]["active"])
        self.assertIn("q=x", chips[1]["url"])
        self.assertIn("section=events", chips[2]["url"])
        # 「全部」chip 剔除 section 自身，保留其余参数。
        self.assertIn("q=x", chips[0]["url"])
        self.assertNotIn("section=", chips[0]["url"])

    def test_type_dept_tag_filters(self):
        data = self.client.get("/api/v1/search?type=article&dept=xgb").json()
        self.assertEqual([e["type"] for e in data["entries"]], ["article"])
        # tag 词表外值视同未提供（200 回退，回显 null）。
        wide = self.client.get("/api/v1/search?q=端点&tag=词表外").json()
        self.assertIsNone(wide["filters"]["tag"])
        self.assertTrue(len(wide["entries"]) >= 1)

    def test_section_filter_scopes_results(self):
        materials = make_container(self.sections["materials"], self.jwc)
        make_material(materials, slug="s-mat", title="资料站内通知", publish=True)
        data = self.client.get("/api/v1/search?q=站内通知&section=materials").json()
        self.assertEqual([e["title"] for e in data["entries"]], ["资料站内通知"])
        self.assertEqual(data["filters"]["section"], "materials")
        self.assertIn(
            ("板块", "学习资料"),
            [(c["label"], c["value"]) for c in data["filters"]["conditions"]],
        )


class DetailEndpointTests(EndpointDataTestCase):
    def test_notice_detail_full_shape(self):
        data = self.client.get(f"/api/v1/pages/{_path(self.notice)}").json()
        self.assertEqual(data["type"], "notice")
        self.assertEqual(data["title"], "端点通知")
        self.assertEqual(data["slug"], "ep-notice")
        self.assertEqual(data["url"], self.notice.url)
        self.assertEqual(data["section"], {"slug": "chronicle", "title": "校园纪事"})
        self.assertEqual(data["department"], {"name": "教务处", "slug": "jwc"})
        self.assertFalse(data["expired"])
        self.assertFalse(data["noindex"])
        self.assertIsNone(data["cover"])
        self.assertIsNotNone(data["expire_at"])
        self.assertEqual(
            data["breadcrumb"],
            [
                {"title": "首页", "url": "/"},
                {"title": "校园纪事", "url": "/chronicle/"},
                {"title": "端点通知", "url": None},
            ],
        )
        self.assertEqual(data["summary"], "测试摘要")
        self.assertIsNone(data["event"])
        self.assertEqual(data["body"][0]["type"], "paragraph")
        self.assertIn("<p>", data["body"][0]["value"]["html"])
        self.assertEqual(data["attachments"], [])
        self.assertIsNone(data["external"])
        self.assertEqual(data["tags"], [])
        self.assertNotIn("preview", data)

    def test_notice_detail_all_six_blocks(self):
        """六块只读投影：标题/段落/图片/附件/表格/外链（确认链出口）。"""
        document = Document.objects.create(
            title="操作手册",
            file=SimpleUploadedFile("manual.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
        )
        image = make_inline_image()
        notice = _save(
            NoticePage(
                title="块测试通知",
                slug="blocks-notice",
                summary="测试摘要",
                department=self.jwc_chronicle.department,
                expire_at=future(),
                body=_body(
                    {"type": "heading", "value": {"text": "小节标题", "level": "h2"}},
                    {"type": "paragraph", "value": "<p>带<b>加粗</b>正文。</p>"},
                    {"type": "image", "value": image.pk},
                    {"type": "attachment", "value": document.pk},
                    {
                        "type": "table",
                        "value": {
                            "data": [["列一", "列二"], ["甲", "乙"]],
                            "first_row_is_table_header": True,
                        },
                    },
                    {
                        "type": "external_link",
                        "value": {
                            "url": "https://files.example.com/a",
                            "link_text": "安装包",
                        },
                    },
                ),
            ),
            self.jwc_chronicle,
            publish=True,
        )
        blocks = self.client.get(f"/api/v1/pages/{_path(notice)}").json()["body"]
        self.assertEqual(
            [b["type"] for b in blocks],
            ["heading", "paragraph", "image", "attachment", "table", "external_link"],
        )
        self.assertEqual(blocks[0]["value"], {"text": "小节标题", "level": "h2"})
        self.assertIn("<b>", blocks[1]["value"]["html"])
        # 1200×800 源 → width-1120 只缩不放（Wagtail 滤镜语义）。
        self.assertEqual(blocks[2]["value"]["width"], 1120)
        self.assertEqual(blocks[2]["value"]["height"], 746)
        self.assertTrue(blocks[2]["value"]["src"].startswith("/media/"))
        self.assertEqual(blocks[2]["value"]["alt"], "测试图片")
        self.assertEqual(blocks[3]["value"]["title"], "操作手册")
        self.assertIn("/documents/", blocks[3]["value"]["url"])
        self.assertEqual(blocks[4]["value"]["data"], [["列一", "列二"], ["甲", "乙"]])
        self.assertTrue(blocks[4]["value"]["first_row_is_table_header"])
        self.assertEqual(blocks[5]["value"]["text"], "安装包")
        self.assertIn(
            "/link-confirm/?url=" + quote("https://files.example.com/a", safe="/"),
            blocks[5]["value"]["confirm_href"],
        )
        self.assertIn(f"from={notice.pk}", blocks[5]["value"]["confirm_href"])

    def test_event_info_serialized(self):
        event = _save(
            NoticePage(
                title="详情活动",
                slug="detail-event",
                summary="测试摘要",
                department=self.jwc_events.department,
                expire_at=future(),
                event_start_at=future(days=2),
                event_end_at=future(days=3),
                event_location="大学生活动中心",
                event_registration_url="https://forms.example.com/r",
                body=json.loads(body_json()),
            ),
            self.jwc_events,
            publish=True,
        )
        data = self.client.get(f"/api/v1/pages/{_path(event)}").json()
        self.assertEqual(data["event"]["status"], "upcoming")
        self.assertEqual(data["event"]["location"], "大学生活动中心")
        self.assertFalse(data["event"]["is_online"])
        self.assertIsNotNone(data["event"]["start_at"])
        self.assertEqual(
            data["event"]["registration"],
            {
                "url": "https://forms.example.com/r",
                "confirm_href": "/link-confirm/?url="
                + quote("https://forms.example.com/r", safe="/")
                + f"&from={event.pk}",
            },
        )

    def test_notice_external_url_ref(self):
        notice = _save(
            NoticePage(
                title="外链通知",
                slug="ext-detail",
                summary="测试摘要",
                department=self.jwc_chronicle.department,
                expire_at=future(),
                external_url="https://example.com/doc",
                body=json.loads(body_json()),
            ),
            self.jwc_chronicle,
            publish=True,
        )
        data = self.client.get(f"/api/v1/pages/{_path(notice)}").json()
        self.assertEqual(data["external"]["url"], "https://example.com/doc")
        self.assertIn("/link-confirm/?url=", data["external"]["confirm_href"])

    def test_material_software_guide_details(self):
        materials = make_container(self.sections["materials"], self.jwc)
        software = make_container(self.sections["software"], self.jwc)
        guide = make_container(self.sections["guide"], self.jwc)
        material = make_material(materials, slug="d-material", title="详情资料", publish=True)
        tool = make_software(software, slug="d-software", title="详情工具", publish=True)
        guide_page = make_guide(guide, slug="d-guide", title="详情指南", publish=True)
        m = self.client.get(f"/api/v1/pages/{_path(material)}").json()
        self.assertEqual(m["type"], "material")
        self.assertEqual(m["discipline"], "计算机科学")
        self.assertEqual(m["material_type"], "课件")
        s = self.client.get(f"/api/v1/pages/{_path(tool)}").json()
        self.assertEqual(s["platforms"], ["Windows"])
        self.assertEqual(s["source"]["url"], "https://example.com/tool")
        self.assertEqual(s["license_note"], "校园授权，免费使用")
        self.assertNotIn("attachments", s)
        g = self.client.get(f"/api/v1/pages/{_path(guide_page)}").json()
        self.assertEqual(g["type"], "guide")
        self.assertEqual(g["maintenance_mode"], "self")
        self.assertEqual(g["maintenance_mode_label"], "责任部门后台自维护")
        self.assertEqual(g["category"], "服务地点")
        self.assertEqual(g["location"], "第一教学楼一层")
        self.assertIn("last_confirmed_on", g)

    def test_expired_detail_allowed_with_flag(self):
        expired = make_notice(self.jwc_chronicle, slug="d-expired", title="到期详情", publish=True)
        expire(expired)
        response = self.client.get(f"/api/v1/pages/{_path(expired)}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["expired"])

    def test_non_live_states_404(self):
        """S0 草稿 404（E6 放行集＝live ∪ expired）。"""
        draft = make_notice(self.jwc_chronicle, slug="d-draft", title="草稿详情")
        response = self.client.get(f"/api/v1/pages/{_path(draft)}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_scheduled_not_yet_live_404(self):
        """S1 预约未到＝404（CURRENT 前置的 live 放行口径）。"""
        scheduled = make_notice(
            self.jwc_chronicle,
            slug="d-scheduled",
            title="预约详情",
            publish=True,
            schedule_at=future(days=2),
        )
        self.assertFalse(scheduled.live)
        self.assertEqual(self.client.get(f"/api/v1/pages/{_path(scheduled)}").status_code, 404)

    def test_unpublished_404(self):
        """S4 下线 404。"""
        notice = make_notice(self.jwc_chronicle, slug="d-unpub", title="下线详情", publish=True)
        notice.unpublish()
        self.assertEqual(self.client.get(f"/api/v1/pages/{_path(notice)}").status_code, 404)

    def test_missing_ancestors_404(self):
        base = "/api/v1/pages"
        self.assertEqual(self.client.get(f"{base}/bogus/jwc/ep-notice").status_code, 404)
        self.assertEqual(self.client.get(f"{base}/chronicle/nobody/ep-notice").status_code, 404)
        self.assertEqual(self.client.get(f"{base}/chronicle/jwc/missing").status_code, 404)

    def test_draft_container_unreachable(self):
        """未发布容器＝路径不可达（Wagtail 路由口径：live 祖先才放行）。"""
        from departments.models import DepartmentContainerPage

        # 一板块一部门一容器（CONTENT_MODEL §4）——草稿容器须用新部门。
        draft_department = make_department("草稿处", "draft-dept")
        container = DepartmentContainerPage(
            title="草稿容器", slug="draft-dept", department=draft_department
        )
        container.live = False  # ORM 默认 True；草稿态须显式（_save 同口径）
        container = self.sections["chronicle"].add_child(instance=container)
        make_notice(container, slug="hidden-in-draft", title="容器内通知", publish=True)
        self.assertEqual(
            self.client.get("/api/v1/pages/chronicle/draft-dept/hidden-in-draft").status_code,
            404,
        )


class SitemapEndpointTests(EndpointDataTestCase):
    def test_loc_path_form_and_container_excluded(self):
        data = self.client.get("/api/v1/sitemap").json()["entries"]
        locs = [item["loc"] for item in data]
        self.assertIn("/", locs)
        self.assertIn(self.notice.url, locs)
        for loc in locs:
            self.assertTrue(loc.startswith("/"))
        # 容器不入 sitemap（DepartmentContainerPage.get_sitemap_urls 空，IA-03）。
        self.assertNotIn("/chronicle/jwc/", locs)
        self.assertNotIn("/chronicle/xgb/", locs)

    def test_live_public_semantics_and_lastmod(self):
        """排除口径＝现状 sitemap.xml（live∧public）。到期页经
        publish_scheduled 已下线（live=False）→ 不入；草稿不入。"""
        expired = make_notice(self.jwc_chronicle, slug="sm-expired", title="站点到期", publish=True)
        make_notice(self.jwc_chronicle, slug="sm-draft", title="站点草稿")
        expire(expired)
        self.assertFalse(expired.live)
        data = self.client.get("/api/v1/sitemap").json()["entries"]
        locs = [item["loc"] for item in data]
        self.assertNotIn(expired.url, locs)
        self.assertNotIn("/chronicle/jwc/sm-draft/", locs)
        entry = next(item for item in data if item["loc"] == self.notice.url)
        self.assertIsNotNone(entry["lastmod"])
