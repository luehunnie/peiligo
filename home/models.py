from datetime import timedelta
from urllib.parse import quote

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator

# 五类内容页模型类直引（FeaturedItem 选择器过滤仅五类，CONTENT_MODEL
# §13.3）：AdminPageChooser 的 target_models 传字符串会在本模块加载期
# （registry 未 ready）解析失败，传类不受此限。home 为首位 app，此处提前
# 拉起 notices/resources/guides 的 models 模块——其只依赖 departments 与
# wagtail，AppConfig 均已创建，类定义合法，无环。
from guides.models import GuidePage
from notices.lifecycle import LIFECYCLE_LIVE
from notices.models import ArticlePage, EventFieldsMixin, NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from search import services as search_services
from wagtail.admin.panels import FieldPanel
from wagtail.admin.widgets import AdminPageChooser
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.models import Page
from wagtail.snippets.models import register_snippet

from peiligo.link_validation import validate_external_url

# 五板块冻结清单（IA §2，中文名与 PRD §6 一字不差；slug 为 §4.3 默认值，
# B 阶段可微调并留痕）。旧站 3 个不一致命名的具体字面量见 IA §2（禁复入），
# 此处不重复书写。
SECTIONS = [
    {"title": "校园纪事", "slug": "chronicle"},
    {"title": "校园活动", "slug": "events"},
    {"title": "学习资料", "slug": "materials"},
    {"title": "软件与工具", "slug": "software"},
    {"title": "校园指南", "slug": "guide"},
]


# 首页数据区展示参数（IA §7.1/§7.2；条数为 MB9 实现阶段展示参数，非架构
# 冻结值）：推荐位有效槽位上限 3（Q14），最新通知 8 条，近期活动 4 条。
FEATURED_MAX_SLOTS = 3
HOMEPAGE_LATEST_NOTICES_COUNT = 8
HOMEPAGE_UPCOMING_EVENTS_COUNT = 4


def _active_alert(site_settings, now):
    """紧急提示展示判定（IA §7.1 层 1；CONTENT_MODEL §13.4 同口径）。

    ``alert_text`` 空（含纯空白）＝无提示；起止成对，双空＝不限期，成对
    填写时须 ``起 ≤ now ≤ 止`` 才展示（窗口语义与 FeaturedItem §15.4
    同口径）。
    """
    text = (site_settings.alert_text or "").strip()
    if not text:
        return None
    start, end = site_settings.alert_start_at, site_settings.alert_end_at
    if start is not None and end is not None and not (start <= now <= end):
        return None
    return {"text": text}


def _featured_entries(now):
    """推荐位有效条目（IA §7.2；Q14/Q15 裁决）。

    槽位上限 3（Q14）、0 条整区不渲染、1–2 条自然呈现；顺序＝创建顺序
    （snippet 无排序字段，§13.3——pk 升序即运营录入顺序，确定性）；有效
    性判定复用 §15.4 ``is_on_display``（enabled∧窗口∧所指内容 S2 live）
    为唯一权威口径——查询集的窗口预过滤仅为少取行，无效条目不占槽位。
    """
    candidates = FeaturedItem.objects.filter(
        enabled=True, start_at__lte=now, end_at__gte=now
    ).order_by("pk")
    entries = []
    for item in candidates:
        if not item.is_on_display(now):
            continue
        entries.append(item.content.specific)
        if len(entries) == FEATURED_MAX_SLOTS:
            break
    return entries


def _latest_notices():
    """最新通知（IA §7.1 层 3）：全站最新且仍有效的通知，发布时间倒序。

    可见性谓词＝CURRENT_DEFAULT（§16.4 live∧¬expired），与
    ``search.services._current_default_search_queryset``/
    ``notices.lifecycle.current_default_pages`` 同一谓词的逐类型形态；
    条数＝MB9 展示参数（``HOMEPAGE_LATEST_NOTICES_COUNT``）。
    """
    return (
        NoticePage.objects.live()
        .filter(expired=False)
        .order_by("-first_published_at")[:HOMEPAGE_LATEST_NOTICES_COUNT]
    )


def _upcoming_events(now, events_section):
    """近期活动（IA §7.1 层 4）：活动板块子树内尚未结束的活动，按开始
    时间升序（时间邻近）。

    活动载体＝通知/文章的结构化活动字段（CONTENT_MODEL §7，无独立活动
    Page）；板块归属经物化路径区间（``path__startswith``，§20.1 表 A
    同一维度语义）。可见性谓词同 CURRENT_DEFAULT；纳入条件＝已填开始且
    ``event_end_at ≥ now``（进行中＋未开始）；通知/文章两模型各取候选
    后合并按开始时间排序截断。
    """
    if events_section is None:
        return []
    pages = []
    for model in (NoticePage, ArticlePage):
        pages.extend(
            model.objects.live()
            .filter(
                expired=False,
                path__startswith=events_section.path,
                event_start_at__isnull=False,
                event_end_at__gte=now,
            )
            .order_by("event_start_at")[:HOMEPAGE_UPCOMING_EVENTS_COUNT]
        )
    pages.sort(key=lambda page: page.event_start_at)
    return pages[:HOMEPAGE_UPCOMING_EVENTS_COUNT]


# 首页校园快讯目标上限（Phase 8C 定稿）：单条统一发现轨至多 3 张卡；
# 上游数据区（推荐位 3/最新通知 8/近期活动 4）维持各自口径不变。
CAMPUS_NEWS_MAX_ITEMS = 3


def _campus_news_entry(page):
    """单条校园快讯展示字典（Phase 8C；纯派生，零落库零新字段）。

    只取既有字段：title/href、cover_image（五类内容页统一轮播封面，
    CoverImageMixin）、一职摘要回落链、板块身份（树上派生 slug）、部门名
    与发布日期（有则展示）、活动状态（既有 event_status 纯计算属性，仅
    填了活动字段的通知/文章存在，其余静默为 None）。
    """
    department = getattr(page, "department", None)
    return {
        "title": page.title,
        "href": page.url,
        "cover": getattr(page, "cover_image", None),
        "summary": Truncator(_content_summary(page)).chars(50),
        "section_slug": _section_slug_of(page),
        "department": str(department) if department else "",
        "date": page.first_published_at,
        "event_status": getattr(page, "event_status", None),
    }


def _campus_news_entries(featured_entries, latest_notices, upcoming_events):
    """校园快讯统一组稿（Phase 8C 定稿：旧首页「推荐/最新通知/近期活动」
    三个独立数据区在本页合并为一条发现轨；后端能力与可见性口径原样保留，
    不删任何 helper/查询）。

    组稿规则（确定性，无推荐引擎）：
    1. 优先已策展的推荐位条目（创建序），再以最新通知（发布倒序）、近期
       活动（开始时间邻近升序）补位——三层输入各自已按上游可见性谓词
       （§15.4/§16.4）过滤，本层不重复判定；
    2. 已结束的活动载体不入轨（8C 产品修订）：候选的既有 ``event_status``
       纯计算属性（§7.1，与卡面「已结束」标注同源）判为已结束即整条跳过
       ——仅本页组稿层过滤，三层输入（含策展条目）一视同仁；不改页面
       可见性（板块/搜索/详情原样可达），也不用已结束内容回填补位；
    3. 同一页面只出现一次（按 pk 去重，先到先得）；
    4. 至多 ``CAMPUS_NEWS_MAX_ITEMS``（3）张；不足自然呈现，0 条由模板
       整区不渲染。纯函数：不改输入、不写库。
    """
    entries = []
    seen = set()
    for page in (*featured_entries, *latest_notices, *upcoming_events):
        if getattr(page, "event_status", None) == EventFieldsMixin.STATUS_ENDED:
            continue
        if page.pk in seen:
            continue
        seen.add(page.pk)
        entries.append(_campus_news_entry(page))
        if len(entries) == CAMPUS_NEWS_MAX_ITEMS:
            break
    return entries


def _content_summary(specific):
    """内容页一职摘要（现有字段回落链，list_row 同序：summary →
    license_note → location；无相应字段或空值返回空串）。

    Phase 8C Hero/校园快讯共用的展示派生：只读既有字段，不新增模型
    字段、不落库；截断长度由消费侧决定（Hero 60 字、快讯卡 50 字）。
    """
    if isinstance(specific, (NoticePage, ArticlePage, MaterialPage)):
        return (specific.summary or "").strip()
    if isinstance(specific, SoftwareToolPage):
        return (specific.license_note or "").strip()
    if isinstance(specific, GuidePage):
        return (specific.location or "").strip()
    return ""


def _section_slug_of(page):
    """页面所属一级板块 slug（祖先树上最近 SectionPage；无所属返回 None）。

    板块身份唯一事实源＝冻结 slug（SECTION_IDENTITY），经祖先树查询实时
    派生，零数据字段零迁移；模板侧经 section_short/section_tone 过滤器
    映射短名与 tone 类（未识别 slug 一律中性回落，不猜色）。
    """
    section = page.get_ancestors().type(SectionPage).first()
    return section.slug if section is not None else None


def _carousel_entries(source_page_id):
    """首页轮播位运行时条目（首页升级 Phase 6 SSR 基座；Hero 与 Search 之间）。

    - 顺序＝模型 ``Meta.ordering``（``sort_order`` 升序、pk 兜底稳定序，
      冻结决策 10），``.all()`` 即按该稳定序读取，不另立排序口径；
    - 运行时逐项复核 ``CarouselItem.is_on_display``（前台可展示最小判定的
      唯一权威消费位）：轮播配置保存后目标内容可能随即 draft/scheduled/
      unpublished/expired，运行时不得继续展示；
    - 失效项静默跳过（单个失效配置不得拖垮首页渲染）。绕过 clean 落库的
      脏数据（站内目标为白名单外结构页——无 lifecycle 推导可得）同按失效
      处理，防 AttributeError；
    - 数量＝按序扫描、过滤后收集至多 ``CAROUSEL_MAX_ITEMS`` 个有效项——
      「先取前 5 再过滤」会让前部失效项永久遮蔽后部合法配置（前台消费侧
      防御语义，冻结决策 11）；
    - 外链项 URL 运行时复用 ``validate_external_url`` 复核（SB §10-7 同源
      规则，零新安全规则），并按既有确认链路 contract 构建 confirm href
      （F-03：/link-confirm/ → /link-confirm/go/ 输出层二次校验不变；编码
      与 ``external_link_jump.html`` 的 ``urlencode`` 过滤器同口径＝
      ``quote(value, safe="/")``；``from`` 引当前首页，仅作确认页来源展示）；
    - Phase 8C 追加两个 DERIVED 展示键（8A 裁决：仅派生、零持久化、零迁移）：
      ``summary``＝页型化一职摘要（``_content_summary`` 现有字段链，截断
      60 字）——外链项一律空串（不虚构库外元数据）；``section_slug``＝
      板块身份（``_section_slug_of`` 树上派生）——外链项与无法判定者
      None，模板回落中性「推荐」chip，不猜板块。
    """
    entries = []
    for item in CarouselItem.objects.all():
        specific = None
        if item.internal_page_id:
            specific = item.internal_page.specific
            if not isinstance(specific, CAROUSEL_INTERNAL_PAGE_TYPES):
                continue
        if not item.is_on_display():
            continue
        if specific is not None:
            href = specific.url
            if not href:
                continue  # 无站内 URL（站点归属异常等）：按失效静默跳过
            entries.append(
                {
                    "kind": "internal",
                    "title": specific.title,
                    "href": href,
                    "cover": specific.cover_image,
                    "summary": Truncator(_content_summary(specific)).chars(60),
                    "section_slug": _section_slug_of(specific),
                }
            )
        else:
            try:
                external_url = validate_external_url(item.external_url)
            except ValidationError:
                continue
            entries.append(
                {
                    "kind": "external",
                    "title": item.external_title.strip(),
                    "href": (
                        f"{reverse('link-confirm')}"
                        f"?url={quote(external_url, safe='/')}&from={source_page_id}"
                    ),
                    "cover": item.external_cover_image,
                    "summary": "",
                    "section_slug": None,
                }
            )
        if len(entries) == CAROUSEL_MAX_ITEMS:
            break
    return entries


class HomePage(Page):
    """首页（第 1 层，全站唯一实例；挂载约束 IA §5）。"""

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "首页"
        verbose_name_plural = "首页"

    parent_page_types = ["wagtailcore.Page"]  # 仅站点根（Wagtail Root）
    subpage_types = ["home.SectionPage"]  # 仅五个一级板块页

    def get_context(self, request, *args, **kwargs):
        """首页模板上下文（Phase 8C 定稿视觉层级）。

        页面结构冻结顺序（Phase 8C，R4-A「Peiligo POP」）：Header → 紧急
        提示（例外性轻量条，无活动提示不渲染）→ Hero 轮播（即原轮播位，
        0 项整区不渲染）→ 五分类导航（真实 SectionPage，冻结顺序）→
        校园快讯 → Footer。旧首页独立「推荐/最新通知/近期活动」区与独立
        搜索卡不再在本页渲染——后端能力（FeaturedItem/通知/活动查询与
        可见性口径）原样保留，由 ``_campus_news_entries`` 统一组稿为至多
        3 条的单一发现轨消费；五分类导航仅查询本页下已发布的 SectionPage
        并按 ``SECTIONS`` 冻结顺序排列（§2 #1–#5），容器不是入口、永不
        进入（§6.2）。轮播位运行时条目见 ``_carousel_entries``（含 Phase
        8C 派生展示键 summary/section_slug）。
        """
        context = super().get_context(request, *args, **kwargs)
        children = {page.slug: page for page in self.get_children().live().type(SectionPage)}
        context["section_entries"] = [
            children[section["slug"]] for section in SECTIONS if section["slug"] in children
        ]
        now = timezone.now()
        context["alert"] = _active_alert(SiteSettings.for_request(request), now)
        context["carousel_items"] = _carousel_entries(self.pk)
        context["featured_entries"] = _featured_entries(now)
        context["latest_notices"] = _latest_notices()
        context["upcoming_events"] = _upcoming_events(now, children.get("events"))
        context["campus_news"] = _campus_news_entries(
            context["featured_entries"], context["latest_notices"], context["upcoming_events"]
        )
        return context


class SectionPage(Page):
    """一级板块页（第 2 层，×5，每板块一页；IA §2/§5）。

    类型名为工作名，正式类型清单与命名由 M3.1 终判（IA §5 表头注）。
    """

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "板块页"
        verbose_name_plural = "板块页"

    parent_page_types = ["home.HomePage"]  # 仅首页
    subpage_types = ["departments.DepartmentContainerPage"]  # 仅部门容器

    def get_context(self, request, *args, **kwargs):
        """板块列表页（IA §6.2＋§9）：默认列表与筛选态共用同一过滤层。

        默认列表＝本板块内容页（第 4 层叶子，容器不是列表项）按发布时间
        倒序；M3.4 起 q/dept/type/tag 四参数生效（§9.1 板块页生效参数），
        ``?section=`` 一律忽略（板块维度由路径唯一决定）。查询委托
        ``search.services``——CURRENT_DEFAULT_SEARCH 可见性（§21.5＝
        §16.4 live∧¬expired 同谓词）、逐类型入口（§20.0 事实 3）、
        filter-first＋保序（§21.6）与 /search/ 完全同层。Phase 8B 起共享
        分页（search.services.paginate_entries，与 /search/ 同一实现；
        content_entries 键名不变，值＝当前页条目）。
        """
        context = super().get_context(request, *args, **kwargs)
        filters = search_services.resolve_section_filters(request.GET, self)
        entries = search_services.search_pages(filters)
        page_obj, page_links = search_services.paginate_entries(entries, request.GET.get("page"))
        context["content_entries"] = page_obj.object_list
        context["total_entries"] = page_obj.paginator.count
        context["page_obj"] = page_obj
        context["page_links"] = page_links
        stripped = request.GET.copy()
        stripped.pop("page", None)
        context["querystring"] = stripped.urlencode()
        context["search_filters"] = filters
        context["filter_active"] = filters.filter_active
        return context


# 推荐位默认有效期 30 天（G2_HUMAN_DECISIONS Q15 裁决：默认 30 天，到期
# 自动停展；提前撤下＝enabled=False，延长＝改 end_at——字段值可编辑，
# 默认值仅作用于新建时留空的表单位）。
FEATURED_DEFAULT_DAYS = 30


def _featured_default_end():
    return timezone.now() + timedelta(days=FEATURED_DEFAULT_DAYS)


@register_snippet
class FeaturedItem(models.Model):
    """首页推荐位（CONTENT_MODEL §13.3；PRD §9；ADR-0005 #13）。

    推荐位呈现所指内容自身的标题/摘要（无文案/图片字段）；展示数量与顺序
    由前台消费侧冻结（无排序字段，前台按创建顺序取有效条目前 3）。仅总
    管理员可管理（§3）。
    """

    content = models.ForeignKey(
        # 推荐位随所指内容删除而失效（运营位无独立保留价值，§13.3）；
        # 选择器过滤仅五类内容页由 panels 的 AdminPageChooser 承载。
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        verbose_name="指向内容",
    )
    # 默认窗口＝自创建时刻起 30 天（Q15）：起＝当前时刻，止＝30 天后
    # （callable default 每次新建表单实时求值）。
    start_at = models.DateTimeField("开始时间", default=timezone.now)
    end_at = models.DateTimeField(
        "结束时间",
        default=_featured_default_end,
        help_text="默认自开始时刻起 30 天，可编辑延长；提前撤下请关闭「启用」",
    )
    enabled = models.BooleanField("启用", default=True)  # 总管理员的即时开关

    panels = [
        FieldPanel(
            "content",
            widget=AdminPageChooser(
                # §13.3：选择器过滤仅五类内容页（容器/板块/首页不可选）。
                target_models=[
                    NoticePage,
                    ArticlePage,
                    MaterialPage,
                    SoftwareToolPage,
                    GuidePage,
                ]
            ),
        ),
        FieldPanel("start_at"),
        FieldPanel("end_at"),
        FieldPanel("enabled"),
    ]

    class Meta:
        verbose_name = "首页推荐位"
        verbose_name_plural = "首页推荐位"

    def __str__(self):
        return self.content.title if self.content_id else "（未指定内容）"

    def clean(self):
        super().clean()
        # §13.3：clean 成对校验 end ≥ start（相等合法口径同 §7.1）。
        if self.end_at < self.start_at:
            raise ValidationError({"end_at": ["结束时间不得早于开始时间（CONTENT_MODEL §13.3）"]})

    def is_on_display(self, now=None):
        """展示有效性四条件合取（§15.4 语义冻结；前台渲染消费归 B 阶段
        前台/M5.2）：``enabled`` ∧ ``start_at ≤ now ≤ end_at`` ∧ 所指页
        ∈ CURRENT_DEFAULT（§16.4）。数量与顺序规则归 IA §7.2，不在本判定。
        """
        now = now or timezone.now()
        return (
            self.enabled
            and self.start_at <= now <= self.end_at
            and self.content.specific.lifecycle_state == LIFECYCLE_LIVE
        )


# 首页轮播位容量（首页升级 Phase 2 冻结决策 11）：上限 5——模型层 clean
# 拒第 6 条新建（编辑既有项不受限）；前台消费侧仍防御性最多取 5。
CAROUSEL_MAX_ITEMS = 5

# CarouselItem 站内目标白名单（Phase 2 冻结决策 4）：仅五类内容页——首页/
# 板块/容器等结构页不可选；与 FeaturedItem 选择器过滤同一集合（本模块顶部
# 直引五类的加载期原因见文件头注）。站内项标题/URL/封面一律取自目标页，
# 本侧不重复配置（冻结决策 5）。
CAROUSEL_INTERNAL_PAGE_TYPES = (
    NoticePage,
    ArticlePage,
    MaterialPage,
    SoftwareToolPage,
    GuidePage,
)


@register_snippet
class CarouselItem(models.Model):
    """首页轮播位条目（首页升级 Phase 2 冻结架构；仅总管理员可管理，§3）。

    站内项与外链项二选一（clean 强制 XOR，冻结决策 3）：站内项只选目标
    内容页，标题/URL 取自目标 Page、封面取自目标页 ``cover_image``；
    外链项自带标题与可选封面，URL 复用
    ``peiligo.link_validation.validate_external_url``（SB §10-7，冻结
    决策 7，不重新实现 validator）。
    """

    internal_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.CASCADE,  # 站内项随目标内容页删除而消失（冻结决策 8）
        related_name="+",
        verbose_name="站内内容页",
    )
    external_url = models.URLField("外部链接", blank=True, validators=[validate_external_url])
    external_title = models.CharField("外链标题", max_length=255, blank=True)
    external_cover_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,  # 封面图删除仅置空，条目保留（冻结决策 9）
        related_name="+",
        verbose_name="外链封面图",
    )
    sort_order = models.PositiveSmallIntegerField("排序", default=0)

    panels = [
        FieldPanel(
            "internal_page",
            widget=AdminPageChooser(target_models=CAROUSEL_INTERNAL_PAGE_TYPES),
        ),
        FieldPanel("external_title"),
        FieldPanel("external_url"),
        FieldPanel("external_cover_image"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        verbose_name = "首页轮播项"
        verbose_name_plural = "首页轮播项"
        ordering = ("sort_order", "pk")  # 重复排序值允许，pk 兜底稳定序（冻结决策 10）

    def __str__(self):
        if self.internal_page_id:
            return self.internal_page.title
        return self.external_title.strip() or "（未指定内容）"

    def clean(self):
        super().clean()
        errors = {}
        # XOR（冻结决策 3）：二选一；外链空白按空处理（strip 口径同 SB §10-7）。
        has_internal = self.internal_page_id is not None
        has_external = bool((self.external_url or "").strip())
        if has_internal and has_external:
            message = ["站内内容页与外部链接只能二选一"]
            errors["internal_page"] = message
            errors["external_url"] = message
        elif not has_internal and not has_external:
            message = ["站内内容页与外部链接必须填写其中一项"]
            errors["internal_page"] = message
            errors["external_url"] = message
        if has_internal:
            # 站内项标题/封面一律取自目标页：外链侧字段必须全空（冻结决策 5）。
            if self.external_title.strip():
                errors["external_title"] = ["站内轮播项不得填写外链标题（标题取自目标内容页）"]
            if self.external_cover_image_id is not None:
                errors["external_cover_image"] = [
                    "站内轮播项不得上传外链封面图（封面取自目标内容页轮播封面图）"
                ]
        if has_external and not self.external_title.strip():
            errors["external_title"] = ["外链轮播项必须填写标题"]
        if has_internal:
            self._clean_internal_target(errors)
        # 位容量（冻结决策 11）：新建第 6 条拒绝；编辑既有项放行——exclude
        # 自身 pk（创建期 pk=None 不排除任何行），GPT REFINEMENT #2。
        if CarouselItem.objects.exclude(pk=self.pk).count() >= CAROUSEL_MAX_ITEMS:
            errors[NON_FIELD_ERRORS] = [f"首页轮播最多 {CAROUSEL_MAX_ITEMS} 条，已达上限"]
        if errors:
            raise ValidationError(errors)

    def _clean_internal_target(self, errors):
        """站内目标类型白名单（冻结决策 4）＋可展示性 canonical 判定
        （GPT REFINEMENT #1）：与 FeaturedItem.is_on_display 同一权威口径
        lifecycle_state == LIFECYCLE_LIVE（§16.4 CURRENT_DEFAULT）——
        draft/scheduled/unpublished/expired 一律拒绝，零新 lifecycle 规则。
        """
        specific = self.internal_page.specific
        if not isinstance(specific, CAROUSEL_INTERNAL_PAGE_TYPES):
            errors["internal_page"] = [
                "轮播站内目标仅支持五类内容页：通知/文章/学习资料/软件工具/校园指南"
            ]
            return
        if specific.lifecycle_state != LIFECYCLE_LIVE:
            errors["internal_page"] = [
                "轮播站内目标当前不可展示：须为已发布且未过期的内容页（当前有效）"
            ]

    def is_on_display(self):
        """前台可展示最小判定（轮播 SSR 消费归后续阶段，本阶段无调用位）。

        站内项＝目标页 lifecycle_state == LIFECYCLE_LIVE（§16.4
        CURRENT_DEFAULT，FeaturedItem.is_on_display 同一谓词）；外链项＝
        URL 与标题均已填（封面可选）。数量/顺序规则归前台消费侧。
        """
        if self.internal_page_id:
            return self.internal_page.specific.lifecycle_state == LIFECYCLE_LIVE
        return bool(self.external_url.strip()) and bool(self.external_title.strip())


@register_setting
class SiteSettings(BaseSiteSetting):
    """站点设置单例（CONTENT_MODEL §13.4；ADR-0005 #14）。

    编辑权限收归总管理员侧（ADR-0004 决策 3 的账号分组与 ADR-0005 替代
    方案 3 遗留要求，权限矩阵 M4.3 落实）。前台消费按区渲染（IA §7.1 层 1
    等）；正式消费切换在 B 阶段前台任务中落实，本模型先落字段与校验。
    """

    alert_text = models.TextField(
        "紧急提示文案", blank=True, help_text="空＝无提示不展示（首页层 1，IA §7.1）"
    )
    alert_start_at = models.DateTimeField("紧急提示起", null=True, blank=True)
    alert_end_at = models.DateTimeField("紧急提示止", null=True, blank=True)
    feedback_email = models.EmailField(
        "统一反馈邮箱",
        help_text="每页反馈链接（自动带内容标题与页面地址）与指南投稿邮箱同源单值",
    )
    redirect_notice_text = models.TextField(
        "跳转页声明文案",
        blank=True,
        help_text="空＝仅渲染 §11.4 四要素结构化信息（域名/来源/时间/变化声明）",
    )

    panels = [
        FieldPanel("alert_text"),
        FieldPanel("alert_start_at"),
        FieldPanel("alert_end_at"),
        FieldPanel("feedback_email"),
        FieldPanel("redirect_notice_text"),
    ]

    def clean(self):
        super().clean()
        # §13.4：提示起止与止同时填/同时空，且止 ≥ 起。
        start, end = self.alert_start_at, self.alert_end_at
        if (start is None) != (end is None):
            raise ValidationError("紧急提示起止时间必须同时填写或同时留空（CONTENT_MODEL §13.4）")
        if start is not None and end < start:
            raise ValidationError({"alert_end_at": ["紧急提示止不得早于起（CONTENT_MODEL §13.4）"]})
