from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# 五类内容页模型类直引（FeaturedItem 选择器过滤仅五类，CONTENT_MODEL
# §13.3）：AdminPageChooser 的 target_models 传字符串会在本模块加载期
# （registry 未 ready）解析失败，传类不受此限。home 为首位 app，此处提前
# 拉起 notices/resources/guides 的 models 模块——其只依赖 departments 与
# wagtail，AppConfig 均已创建，类定义合法，无环。
from guides.models import GuidePage
from notices.lifecycle import LIFECYCLE_LIVE
from notices.models import ArticlePage, NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from search import services as search_services
from wagtail.admin.panels import FieldPanel
from wagtail.admin.widgets import AdminPageChooser
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.models import Page
from wagtail.snippets.models import register_snippet

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


class HomePage(Page):
    """首页（第 1 层，全站唯一实例；挂载约束 IA §5）。"""

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "首页"
        verbose_name_plural = "首页"

    parent_page_types = ["wagtailcore.Page"]  # 仅站点根（Wagtail Root）
    subpage_types = ["home.SectionPage"]  # 仅五个一级板块页

    def get_context(self, request, *args, **kwargs):
        """首页模板上下文：四数据区＋五板块入口网格（IA §7.1 层 1–4）。

        层 1 紧急提示（SiteSettings 站点级配置）、层 2 推荐位（FeaturedItem
        snippet）、层 3 最新通知、层 4 近期活动——各数据区空则模板整区不
        渲染（§7.1），层内相对顺序冻结、查询与渲染口径见各 helper。层 4
        之后的五板块入口网格仅查询本页下已发布的 SectionPage 并按
        ``SECTIONS`` 冻结顺序排列（§2 #1–#5）；容器不是入口、永不进入
        网格（§6.2——经 ``subpage_types`` 白名单 + ``type()`` 过滤天然
        只含板块页）。
        """
        context = super().get_context(request, *args, **kwargs)
        children = {page.slug: page for page in self.get_children().live().type(SectionPage)}
        context["section_entries"] = [
            children[section["slug"]] for section in SECTIONS if section["slug"] in children
        ]
        now = timezone.now()
        context["alert"] = _active_alert(SiteSettings.for_request(request), now)
        context["featured_entries"] = _featured_entries(now)
        context["latest_notices"] = _latest_notices()
        context["upcoming_events"] = _upcoming_events(now, children.get("events"))
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
        filter-first＋保序（§21.6）与 /search/ 完全同层。分页为 MB 阶段
        任务，V1 全量单页渲染。
        """
        context = super().get_context(request, *args, **kwargs)
        filters = search_services.resolve_section_filters(request.GET, self)
        context["content_entries"] = search_services.search_pages(filters)
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
