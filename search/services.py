"""M3.4 搜索服务层：稳定筛选 helper 与逐类型查询入口（CONTENT_MODEL §20–§24）。

本模块是全站搜索页（``/search/``）与板块列表页（``/<板块>/``）共用的同一
过滤层（§21.1 双载体）：

- 稳定过滤 helper：section/dept/type/tag 四维＋可见性谓词，非法值一律
  视同未提供（§21.3，200 回退全量，不 404/不 5xx）；
- 逐类型查询入口：搜索对象域＝五类内容页（§21.1），按 §20.0 事实 3
  （查询期字段集按查询集模型类解析）对五类各查一次后合并，结构性排除
  结构页/容器/Snippet/设置；跨类型合并排序键＝``-first_published_at``
  （§21.6）；
- 执行模型＝filter-first（§21.6）：queryset 先施加全部维度过滤＋可见性
  谓词，再 ``.search(q, order_by_relevance=False)``（保序旋钮，三后端
  一致可表达）；q 空串不进搜索后端（纯 ORM）。
"""

from departments.models import Department
from django.db.models import Q
from guides.models import GuideCategory, GuidePage
from notices.lifecycle import VISIBILITY_CURRENT_DEFAULT, VISIBILITY_HISTORICAL
from notices.models import ArticlePage, NoticePage, Tag
from resources.models import Discipline, MaterialPage, MaterialType, Platform, SoftwareToolPage

# §21.1：section 合法值＝五冻结 slug（IA §2；P4 伪板块页禁入）。
SECTION_SLUGS = ("chronicle", "events", "materials", "software", "guide")

# §21.1/§1.2：type 五值单射（工作名→正式 Model）；中文标签＝§1.1 冻结类型名。
TYPE_IDENTIFIERS = {
    "notice": NoticePage,
    "article": ArticlePage,
    "material": MaterialPage,
    "software": SoftwareToolPage,
    "guide": GuidePage,
}
TYPE_LABELS = {
    "notice": "通知页",
    "article": "文章页",
    "material": "学习资料页",
    "software": "软件与工具页",
    "guide": "校园指南页",
}

# 搜索对象域（§21.1）＝TYPE_IDENTIFIERS 值集（单射即同构）。
SEARCHABLE_PAGE_MODELS = tuple(TYPE_IDENTIFIERS.values())


def model_for_type(value):
    """type 参数 → 正式 Model；未知值视同未提供（None，§21.3）。"""
    return TYPE_IDENTIFIERS.get(value)


def type_identifier(model):
    """正式 Model → type 标识（回显/断言用；域外模型返回 None）。"""
    for identifier, candidate in TYPE_IDENTIFIERS.items():
        if candidate is model:
            return identifier
    return None


def resolve_tag_value(value):
    """tag 值词表校验（§21.2）：命中 Tag（slug∪name）或四类别词表 name
    之一即为合法，返回原值；词表外值视同未提供（None，§21.3）。

    返回的是字面值——谓词按类型通道展开在 ``_tag_condition``（同名并集＝
    各命中谓词之 OR，§21.2）；值的适用类型与 type=/路径板块不相符 →
    该类型查询自然为空＝合法空结果（非错误）。
    """
    if not value:
        return None
    hit = (
        Tag.objects.filter(Q(slug=value) | Q(name=value)).exists()
        or Discipline.objects.filter(name=value).exists()
        or MaterialType.objects.filter(name=value).exists()
        or Platform.objects.filter(name=value).exists()
        or GuideCategory.objects.filter(name=value).exists()
    )
    return value if hit else None


class SearchFilters:
    """解析后的筛选状态（§21.1–§21.3）：None＝该维未提供/非法回退。"""

    def __init__(
        self,
        *,
        q="",
        section=None,
        department=None,
        page_type=None,
        tag=None,
        section_from_path=False,
    ):
        self.q = q
        self.section = section  # SectionPage（路径区间锚点）
        self.department = department  # Department（is_active 词表内）
        self.page_type = page_type  # 正式 Model
        self.tag = tag  # 词表内字面值
        # 板块维度来源标记：板块页由路径锚定（非用户参数），不计入
        # filter_active——否则板块页无参数零内容会误判"筛选无匹配"而非
        # "全空"（IA §11 两空态分界＝用户施加的条件，非载体基线）。
        self.section_from_path = section_from_path

    @property
    def type_identifier(self):
        return type_identifier(self.page_type) if self.page_type else None

    @property
    def filter_active(self):
        """有效筛选态（IA §11 两空态分界依据＝用户施加的解析后条件，
        非原始参数；路径锚定的板块维度不计入）。"""
        return bool(
            self.q
            or (self.section is not None and not self.section_from_path)
            or self.department
            or self.page_type
            or self.tag
        )

    def active_conditions(self):
        """已选条件回显（IA §11 筛选无匹配态）：[(标签, 值), ...]。"""
        conditions = []
        if self.q:
            conditions.append(("关键词", self.q))
        if self.section:
            conditions.append(("板块", self.section.title))
        if self.department:
            conditions.append(("部门", self.department.name))
        if self.page_type:
            conditions.append(("内容类型", TYPE_LABELS[self.type_identifier]))
        if self.tag:
            conditions.append(("标签", self.tag))
        return conditions


def _resolve_section(value):
    """section 值 → SectionPage：仅五冻结 slug 且树内实存，否则 None。

    ``SectionPage`` 迟导入：home.models 反向消费本模块（板块页共用过滤
    层），模块级互指成环；函数期导入时双方均已就绪。
    """
    from home.models import SectionPage

    if value not in SECTION_SLUGS:
        return None
    return SectionPage.objects.live().filter(slug=value).first()


def _resolve_department(value):
    """dept 值 → Department：is_active 词表内 slug（§21.1；停用＝未知值）。"""
    if not value:
        return None
    return Department.objects.filter(slug=value, is_active=True).first()


def resolve_search_filters(params):
    """全站搜索页五参数解析（§21.1：q/section/dept/type/tag 全可选）。"""
    return SearchFilters(
        q=params.get("q", "").strip(),
        section=_resolve_section(params.get("section", "")),
        department=_resolve_department(params.get("dept", "")),
        page_type=model_for_type(params.get("type", "")),
        tag=resolve_tag_value(params.get("tag", "")),
    )


def resolve_section_filters(params, section):
    """板块页四参数解析（§21.1）：板块维度由路径唯一决定——``?section=``
    一律忽略（不读即忽略；含合法值亦然），``section``＝该板块页实例
    （路径区间锚点）。"""
    return SearchFilters(
        q=params.get("q", "").strip(),
        section=section,
        department=_resolve_department(params.get("dept", "")),
        page_type=model_for_type(params.get("type", "")),
        tag=resolve_tag_value(params.get("tag", "")),
        section_from_path=True,
    )


def _tag_condition(model, value):
    """tag 谓词按类型通道展开（§21.2 表）：Tag 双通道（N/A/M）∨ 各类型
    适用词表 name 精确；同名并集＝OR，无优先级。"""
    channels = []
    if model in (NoticePage, ArticlePage, MaterialPage):
        channels.extend([Q(tags__slug=value), Q(tags__name=value)])
    if model is MaterialPage:
        channels.extend([Q(discipline__name=value), Q(material_type__name=value)])
    if model is SoftwareToolPage:
        channels.append(Q(platforms__name=value))
    if model is GuidePage:
        channels.append(Q(category__name=value))
    condition = channels[0]
    for channel in channels[1:]:
        condition |= channel
    return condition


def _current_default_search_queryset(model):
    """CURRENT_DEFAULT_SEARCH＝§16.4 同谓词 live ∧ ¬expired（§21.5/PS-33；
    draft/scheduled 未到点/unpublished/expired 一律不入，与
    ``notices.lifecycle.current_default_pages`` 同一谓词的逐类型形态——
    基类 queryset 无法承载逐类型 search_fields 解析，§20.0 事实 3）。"""
    return model.objects.live().filter(expired=False)


def _historical_search_queryset(model):
    """ARCHIVE-SEARCH/HISTORICAL＝§16.4 放宽谓词 ``Q(live) ∪ Q(expired)``
    （M5.2 §7.1，S2 ∪ S3 状态中性——过期通知与过期文章同入，§7.1 类型
    口径裁决；FilterField("expired") 已声明，零结构变更/零新增索引字段）。
    与 ``_current_default_search_queryset`` 同源的逐类型形态（§6.2-2）；
    消费位＝/search/ 搜索入口与板块归档视图，板块默认列表入口不消费
    （§7 入口绑定义务，PA-31 守门）。"""
    return model.objects.filter(Q(live=True) | Q(expired=True))


def _visibility_queryset(model, visibility):
    """入口绑定的可见性谓词分发（§7）：默认 CURRENT_DEFAULT（保守缺省——
    未显式绑定口径的调用方不得意外放宽），HISTORICAL 仅由搜索入口与
    归档视图显式传入。"""
    if visibility == VISIBILITY_HISTORICAL:
        return _historical_search_queryset(model)
    return _current_default_search_queryset(model)


def _per_type_queryset(model, filters, visibility=VISIBILITY_CURRENT_DEFAULT):
    """filter-first 组合执行（§21.6）：全部维度过滤＋可见性谓词先施加，
    再检索。板块维度＝path 路径区间（§20.1 表 A FilterField("path")：
    ``path__startswith`` 即板块子树路径区间；§21.1 板块维度语义）。"""
    queryset = _visibility_queryset(model, visibility)
    if filters.section is not None:
        queryset = queryset.filter(path__startswith=filters.section.path)
    if filters.department is not None:
        queryset = queryset.filter(department__slug=filters.department.slug)
    if filters.tag is not None:
        queryset = queryset.filter(_tag_condition(model, filters.tag))
    queryset = queryset.order_by("-first_published_at")
    if filters.q:
        # 保序旋钮（§21.6）：默认 order_by_relevance=True 会以相关度整体
        # 替换 queryset 排序（E2/E3）；显式 False 使 -first_published_at
        # 保序成立，且排序键经 check() 三后端一致校验（表 A 已声明）。
        queryset = queryset.search(filters.q, order_by_relevance=False)
    return queryset


def search_pages(filters, visibility=VISIBILITY_CURRENT_DEFAULT):
    """按筛选状态返回五类内容页结果（§21.1 逐类型查询＋合并）。

    type 已提供 → 仅查该类型；否则五类型各查一次（事实 3）。合并排序键
    ＝-first_published_at（§21.6，各类型内已保序，Python 稳定合并）。
    返回逐类型 specific 实例列表（渲染直接消费）。

    ``visibility``＝入口绑定（§7 补充口径，M5.2）：板块默认列表入口
    （SectionPage，含 q 筛选态）缺省 CURRENT_DEFAULT；/search/ 搜索入口
    传 HISTORICAL（ARCHIVE-SEARCH：expired 默认命中并标注，§7.1）；
    板块归档视图传 HISTORICAL（§6.1）。共用代码层不固定口径、由入口
    显式绑定，expired 不得经共用层泄入默认列表（PA-31）。
    """
    models = (filters.page_type,) if filters.page_type else SEARCHABLE_PAGE_MODELS
    merged = []
    for model in models:
        merged.extend(_per_type_queryset(model, filters, visibility))
    # 降序稳定排序：同刻并列保持类型顺序（notice→…→guide）。
    merged.sort(
        key=lambda page: (page.first_published_at is not None, page.first_published_at),
        reverse=True,
    )
    return merged


# §23 金标集挂接点（仅契约占位，不建数据集——30 条本体归 M6.1）：条目
# 四字段结构＋PoC 五字段契约；后续阶段按此引用，不另行发明字段名。

GOLDEN_SET_ENTRY_FIELDS = ("query", "expected_pages", "required_filters", "notes")
POC_FIELD_CONTRACT = ("title", "body", "department", "tags", "category")
