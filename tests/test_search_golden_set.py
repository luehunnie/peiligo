"""F-01 金标集功能回归（POC_SEARCH_REPORT §3.2 冻结表 30 条，SE-01 真源）。

锚点页按 §3.2 规格要点植入：锚点页名＝语体示例可替换，**命中不变式不可
变**——每条金标的 query/expected_pages/required_filters 与 §3.2 逐字段
一致；A 档条目完整查询串仅出现于 expected 页（§2.9-1 负例的功能级等效：
单锚点 A 档断言精确集）；干扰页 P035–P044（"补办/换发"同族指南）不含
"学生证补办"完整串，且 first_published_at 全部早于锚点页（§3.1 时间戳
不变式的功能级等效）。

执行口径＝POC §4.4：required_filters 施加 §21.1–§21.2 维度过滤＋可见性
谓词 ``live ∧ ¬expired``（§21.5＝CURRENT_DEFAULT），经
``services.search_pages`` 生产路径执行（order_by_relevance=False，
-first_published_at 保序）；hit@10 判据＝expected_pages ⊆ top10（§4.1）；
无结果条目（Q21/Q29）＝结果集为空。

边界：本测为功能回归（批令 §8）；放量（200/1000/5000）与逐条 p50 计时
＝VALIDATION_ONLY（NF-17 复验门），不属本测。
"""

import datetime as dt
import json

from django.utils import timezone
from guides.models import GuideCategory, GuidePage
from notices.models import NoticePage, Tag
from resources.models import Discipline, MaterialPage, MaterialType, Platform, SoftwareToolPage
from search import services
from wagtail.models import Page
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import _save, build_sections, future, make_container, make_department


def _body(text):
    """指定正文文本的 StreamField 值（单段落）。"""
    return json.loads(json.dumps([{"type": "paragraph", "value": f"<p>{text}</p>"}]))


# §2.8 部门代号（8 个，is_active 语义）。
DEPARTMENTS = (
    ("教务处", "jwc"),
    ("学工部", "xgb"),
    ("学生处", "xsc"),
    ("图书馆", "tsg"),
    ("财务处", "cwc"),
    ("信息中心", "cpc"),
    ("校团委", "tw"),
    ("人事处", "rsc"),
)

# 锚点页（§3.2 规格要点）：(page_id, 类型, 板块, 部门, 标题, 正文补充, extra)。
# extra：tags＝受控标签；event＝活动板块通知（EventFieldsMixin 必填）；
# location/discipline/material_type/category/platforms＝对应自有检索字段。
ANCHORS = (
    ("P001", "notice", "chronicle", "tw", "关于举办第十二届校园文化艺术节的通知", "", {}),
    ("P002", "notice", "chronicle", "xgb", "校奖学金评定办法", "", {}),
    (
        "P003",
        "notice",
        "chronicle",
        "xgb",
        "奖学金评选工作通知",
        "本年度奖学金评定工作按修订办法执行。",
        {},
    ),
    (
        "P004",
        "notice",
        "chronicle",
        "cwc",
        "关于调整差旅费标准的通知",
        "差旅费报销标准调整如下。",
        {},
    ),
    ("P005", "notice", "chronicle", "tsg", "图书借阅规则", "", {}),
    ("P006", "notice", "chronicle", "jwc", "教室借用通知", "", {}),
    ("P007", "notice", "chronicle", "jwc", "选课通知", "", {}),
    ("P008", "notice", "chronicle", "jwc", "期末考试安排", "", {}),
    ("P009", "guide", "guide", "xgb", "毕业生离校手续指南", "", {}),
    (
        "P010",
        "guide",
        "guide",
        "xgb",
        "宿舍生活指南",
        "问：宿舍晚上几点开始熄灯断电？答：周日至周四 23:00。",
        {},
    ),
    ("P011", "notice", "chronicle", "xsc", "学生处年度工作安排", "学生处统筹全校学生事务。", {}),
    ("P012", "notice", "chronicle", "tsg", "逸夫图书馆暑期开放安排", "", {}),
    ("P013", "notice", "chronicle", "jwc", "四六级报名通知", "", {}),
    (
        "P014",
        "material",
        "materials",
        "jwc",
        "数据结构答疑课件",
        "",
        {"discipline": "计算机类", "material_type": "课件"},
    ),
    (
        "P015",
        "notice",
        "events",
        "tw",
        "秋季运动会规程",
        "",
        {"event": True, "event_location": "田径场"},
    ),
    ("P016", "guide", "guide", "tsg", "校医院门诊指南", "", {"location": "校医院门诊楼一层"}),
    ("P017", "software", "software", "cpc", "WPS 使用指南", "", {"platforms": ("Windows",)}),
    (
        "P018",
        "guide",
        "guide",
        "tw",
        "体育馆使用指南",
        "问：体育馆开放时间是怎样安排的？答：工作日 6:00–21:00。",
        {},
    ),
    ("P019", "notice", "chronicle", "jwc", "实验室开放申请", "", {}),
    (
        "P020",
        "notice",
        "chronicle",
        "tw",
        "学术讲座预告：校史研究前沿",
        "",
        {"tags": ("学术讲座",)},
    ),
    (
        "P021",
        "notice",
        "events",
        "tw",
        "校园歌手大赛报名通知",
        "",
        {"event": True, "event_location": "大学生活动中心"},
    ),
    ("P022", "notice", "chronicle", "cwc", "学费缴费通知", "", {}),
    ("P024", "guide", "guide", "xsc", "学生证补办指南", "", {}),
    ("P025", "guide", "guide", "xsc", "校园卡补办指南", "", {}),
    ("P026", "guide", "guide", "tsg", "图书证挂失补办", "", {}),
    ("P027", "software", "software", "cpc", "MATLAB 下载指引", "", {"platforms": ("Windows",)}),
    ("P028", "notice", "chronicle", "xsc", "在读证明办理通知", "", {}),
    ("P029", "material", "materials", "jwc", "线代习题课", "线性代数习题课配套资料。", {}),
    (
        "P030",
        "notice",
        "events",
        "xgb",
        "春季招聘会指南",
        "",
        {"tags": ("就业招聘",), "event": True, "event_location": "大学生活动中心"},
    ),
    (
        "P031",
        "guide",
        "guide",
        "tsg",
        "自习座位预约指南",
        "问：如何在图书馆预约自习座位？答：入馆系统内选座。",
        {},
    ),
    ("P032", "notice", "chronicle", "xsc", "大学生医保参保通知", "", {}),
    ("P034", "guide", "guide", "jwc", "教育实习基地指南", "", {}),
)

# Q22 干扰页（§3.1：P035–P044 "补办/换发"同族指南，不含"学生证补办"完整串）。
INTERFERENCE = (
    "饭卡补办指引",
    "门禁卡换发流程",
    "澡票补办说明",
    "健康证补办指引",
    "乘车卡补办流程",
    "借书证换发通知",
    "毕业证补办流程",
    "学位证补办流程",
    "普通话证书补办指引",
    "体检卡补办指南",
)

# 金标 30 条（§3.2 冻结表逐字段）：(ID, query, expected_pages, required_filters)。
GOLDEN = (
    ("Q01", "关于举办第十二届校园文化艺术节的通知", ("P001",), {}),
    ("Q02", "奖学金评定", ("P002", "P003"), {}),
    ("Q03", "报销", ("P004",), {}),
    ("Q04", "借", ("P005", "P006"), {}),
    ("Q05", "选课", ("P007",), {}),
    ("Q06", "期末考试", ("P008",), {}),
    ("Q07", "毕业生离校手续", ("P009",), {}),
    ("Q08", "宿舍晚上几点开始熄灯断电", ("P010",), {}),
    ("Q09", "学生处", ("P011",), {}),
    ("Q10", "逸夫图书馆", ("P012",), {}),
    ("Q11", "四六级", ("P013",), {}),
    ("Q12", "数据结构", ("P014",), {}),
    ("Q13", "运动会", ("P015",), {}),
    ("Q14", "校医院", ("P016",), {}),
    ("Q15", "WPS", ("P017",), {}),
    ("Q16", "体育馆开放时间", ("P018",), {}),
    ("Q17", "申请", ("P019",), {"dept": "jwc"}),
    ("Q18", "讲座", ("P020",), {"tag": "学术讲座"}),
    ("Q19", "报名", ("P021",), {"section": "events"}),
    ("Q20", "缴费", ("P022",), {"section": "chronicle", "dept": "cwc"}),
    ("Q21", "量子计算机采购招标", (), {}),
    ("Q22", "学生证补办", ("P024",), {}),
    ("Q23", "下载", ("P027",), {"type": "software"}),
    ("Q24", "证明", ("P028",), {"dept": "xsc"}),
    ("Q25", "线性代数", ("P029",), {}),
    ("Q26", "招聘会", ("P030",), {"tag": "就业招聘"}),
    ("Q27", "如何在图书馆预约自习座位", ("P031",), {}),
    ("Q28", "医保", ("P032",), {}),
    ("Q29", "考研辅导班退费", (), {}),
    ("Q30", "实习", ("P034",), {"section": "guide"}),
)

# A 档单锚点条目（§3.2 负例档位标注）：完整查询串仅出现于 expected 页，
# 故断言**精确集**（§2.9-1 负例校验的功能级等效）；Q21/Q29＝空集。
GRADE_A_EXACT = {"Q01", "Q07", "Q08", "Q16", "Q22", "Q27"}
GRADE_A_EMPTY = {"Q21", "Q29"}


class GoldenSetRegressionTests(WagtailPageTestCase):
    """30 条金标 × E1 生产路径（services.search_pages）功能回归。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        depts = {slug: make_department(name, slug) for name, slug in DEPARTMENTS}
        # 金标所需受控标签（§2.8 词表取值；slug 显式给定避免派生碰撞）。
        golden_tags = (
            ("学术讲座", "golden-xueshu-jiangzuo"),
            ("就业招聘", "golden-jiuye-zhaopin"),
        )
        for name, slug in golden_tags:
            Tag.objects.get_or_create(name=name, defaults={"slug": slug})
        containers = {}

        def container_for(section_slug, dept):
            key = (section_slug, dept.slug)
            if key not in containers:
                containers[key] = make_container(cls.sections[section_slug], dept)
            return containers[key]

        def build(pid, kind, section_slug, dept_slug, title, body_text, extra):
            container = container_for(section_slug, depts[dept_slug])
            common = {"title": title, "slug": pid.lower()}
            tags = extra.get("tags")
            if kind == "notice":
                page = NoticePage(
                    summary=f"{title}摘要",
                    department=container.department,
                    expire_at=future(),
                    body=_body(body_text or "常规事项说明。"),
                    **common,
                )
                if extra.get("event"):
                    page.event_start_at = future(days=3)
                    page.event_end_at = future(days=4)
                    page.event_location = extra.get("event_location", "校内场地")
            elif kind == "material":
                page = MaterialPage(
                    summary=f"{title}摘要",
                    department=container.department,
                    discipline=Discipline.objects.get_or_create(
                        name=extra.get("discipline", "通识")
                    )[0],
                    material_type=MaterialType.objects.get_or_create(
                        name=extra.get("material_type", "课件")
                    )[0],
                    body=_body(body_text or "资料说明。"),
                    **common,
                )
            elif kind == "software":
                page = SoftwareToolPage(
                    department=container.department,
                    platforms=[
                        Platform.objects.get_or_create(name=name)[0]
                        for name in extra.get("platforms", ("Windows",))
                    ],
                    source_url=f"https://example.com/{pid.lower()}",
                    license_note="校园授权，免费使用",
                    body=_body(body_text or "工具说明。"),
                    **common,
                )
            else:
                page = GuidePage(
                    department=container.department,
                    category=GuideCategory.objects.get_or_create(
                        name=extra.get("category", "办事服务")
                    )[0],
                    location=extra.get("location", "办事大厅"),
                    opening_hours="工作日 8:00–17:00",
                    contact="0000-0000000",
                    responsible_party=container.department.name,
                    maintenance_mode="self",
                    last_confirmed_on=timezone.now().date(),
                    extra_notes=body_text,
                    **common,
                )
            published = _save(page, container, publish=True)
            if tags:
                published.tags.set(list(Tag.objects.filter(name__in=tags)))
                published.save_revision().publish()
            return published

        cls.pages = {row[0]: build(*row) for row in ANCHORS}
        interference = [
            build(
                f"P{35 + i}",
                "guide",
                "guide",
                ("xsc", "tsg", "jwc", "xgb", "tw")[i % 5],
                title,
                "",
                {},
            )
            for i, title in enumerate(INTERFERENCE)
        ]

        # §3.1 时间戳不变式（功能级）：锚点页互异且全部晚于干扰页。
        base = timezone.now()
        for i, page in enumerate(cls.pages.values()):
            Page.objects.filter(pk=page.pk).update(
                first_published_at=base - dt.timedelta(minutes=i + 1)
            )
        for i, page in enumerate(interference):
            Page.objects.filter(pk=page.pk).update(
                first_published_at=base - dt.timedelta(days=365, minutes=i + 1)
            )

    def _top_slugs(self, query, filters):
        resolved = services.resolve_search_filters({"q": query, **filters})
        results = services.search_pages(resolved, visibility=services.VISIBILITY_CURRENT_DEFAULT)
        return [page.slug for page in results]

    def test_golden_30_hit_semantics(self):
        for gid, query, expected, filters in GOLDEN:
            with self.subTest(golden=gid):
                got = self._top_slugs(query, filters)
                if gid in GRADE_A_EMPTY:
                    self.assertEqual(got, [])
                    continue
                top10 = got[:10]
                expected_slugs = [pid.lower() for pid in expected]
                for slug in expected_slugs:
                    self.assertIn(slug, top10)
                if gid in GRADE_A_EXACT:
                    self.assertEqual(sorted(got), sorted(expected_slugs))
