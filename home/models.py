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


class HomePage(Page):
    """首页（第 1 层，全站唯一实例；挂载约束 IA §5）。"""

    parent_page_types = ["wagtailcore.Page"]  # 仅站点根（Wagtail Root）
    subpage_types = ["home.SectionPage"]  # 仅五个一级板块页

    def get_context(self, request, *args, **kwargs):
        """首页模板上下文：五板块入口网格（IA §7.1 层 4）。

        仅查询本页下已发布的 SectionPage 并按 ``SECTIONS`` 冻结顺序排列
        （§2 #1–#5）；容器不是入口、永不进入网格（§6.2——本查询经
        ``subpage_types`` 白名单 + ``type()`` 过滤，天然只含板块页）。
        首页其余数据区（紧急提示/推荐位/最新通知/近期活动，§7.1 层 1–3）
        依赖 M3 模型，本步不查询、不渲染（无数据不得显示假内容）。
        """
        context = super().get_context(request, *args, **kwargs)
        children = {page.slug: page for page in self.get_children().live().type(SectionPage)}
        context["section_entries"] = [
            children[section["slug"]] for section in SECTIONS if section["slug"] in children
        ]
        return context


class SectionPage(Page):
    """一级板块页（第 2 层，×5，每板块一页；IA §2/§5）。

    类型名为工作名，正式类型清单与命名由 M3.1 终判（IA §5 表头注）。
    """

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


@register_snippet
class FeaturedItem(models.Model):
    """首页推荐位（CONTENT_MODEL §13.3；PRD §9；ADR-0005 #13）。

    推荐位呈现所指内容自身的标题/摘要（无文案/图片字段）；展示数量与顺序
    由前台消费侧冻结（无排序字段）。仅总管理员可管理（§3）。
    """

    content = models.ForeignKey(
        # 推荐位随所指内容删除而失效（运营位无独立保留价值，§13.3）；
        # 选择器过滤仅五类内容页由 panels 的 AdminPageChooser 承载。
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        verbose_name="指向内容",
    )
    start_at = models.DateTimeField("开始时间")
    end_at = models.DateTimeField("结束时间")
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
