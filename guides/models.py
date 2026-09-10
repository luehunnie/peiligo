"""校园指南页与指南类别词表（CONTENT_MODEL §10/§13.2）。

PRD §7.6 统一九字段一字不差、一个不删（含看似重复者，任务批令冻结）；
无 StreamField 正文、无图片/附件/外部链接/标签字段（§10.1 无字段声明）。
维护治理（自维护/邮箱投稿、每学期复核）为运营流程，不建提醒模型。
"""

from departments.forms import ParentContextPageForm
from departments.models import SectionContextMixin, clean_content_page
from django.core.exceptions import ValidationError
from django.db import models
from notices.lifecycle import EXPIRE_FORBIDDEN, LifecycleStateMixin, clean_publish_window
from notices.models import SEARCH_BOOST_LOW, content_search_fields
from wagtail.admin.panels import FieldPanel, TitleFieldPanel
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from peiligo.cover import CoverImageMixin
from peiligo.seo import SeoControlMixin


@register_snippet
class GuideCategory(models.Model):
    """指南类别词表（CONTENT_MODEL §13.2；食堂/场馆/服务地点类目由词表维护）。

    词表由总管理员维护；被引用（FK PROTECT）时删除受保护（DEFERRED_TO_M3_3）。
    """

    name = models.CharField("名称", max_length=100, unique=True)
    sort_order = models.IntegerField("排序", default=0)

    panels = [FieldPanel("name"), FieldPanel("sort_order")]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "指南类别"
        verbose_name_plural = "指南类别"

    def __str__(self):
        return self.name


class GuidePage(SectionContextMixin, LifecycleStateMixin, CoverImageMixin, SeoControlMixin, Page):
    """校园指南页（CONTENT_MODEL §10；PRD §7.6）。

    九字段＝#1 服务名称（title 映射，不双轨命名）/#2 指南类别/#3 地点/
    #4 开放时间/#5 联系方式/#6 补充说明（仅此项可选）/#7 责任来源或责任单位/
    #8 维护方式（两选项逐源 PRD 原文）/#9 最后确认日期或更新时间
    （显式业务字段，承载人工确认语义——CMS 时间戳不承载，CM-06）；
    expire_at clean 强制空（§16.1，与 02 S5.1"指南不设"口径一致）；
    生命周期五状态零字段纯推导（§14）。
    """

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "校园指南页"
        verbose_name_plural = "校园指南页"

    parent_page_types = ["departments.DepartmentContainerPage"]  # 唯一父级（§1.4）
    subpage_types = []  # 叶子（§1.4）
    ALLOWED_SECTIONS = {"guide"}  # §1.4 板块级限制
    base_form_class = ParentContextPageForm

    category = models.ForeignKey(GuideCategory, on_delete=models.PROTECT, verbose_name="指南类别")
    location = models.CharField("地点", max_length=200)
    opening_hours = models.TextField("开放时间")
    contact = models.TextField("联系方式")
    extra_notes = models.TextField("补充说明", blank=True)  # 九字段中唯一可选项
    responsible_party = models.CharField("责任来源或责任单位", max_length=200)
    maintenance_mode = models.CharField(
        "维护方式",
        max_length=20,
        choices=[
            ("self", "责任部门后台自维护"),
            ("curated", "统一邮箱投稿·总管理员代维护"),
        ],
    )
    last_confirmed_on = models.DateField("最后确认日期或更新时间")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        verbose_name="发布部门",
    )

    # panels 顺序＝§10.2 冻结行序（标题界面标签"服务名称"，映射不删字段）。
    content_panels = [
        TitleFieldPanel("title", heading="服务名称"),
        FieldPanel("department"),
        FieldPanel("category"),
        FieldPanel("location"),
        FieldPanel("opening_hours"),
        FieldPanel("contact"),
        FieldPanel("extra_notes"),
        FieldPanel("responsible_party"),
        FieldPanel("maintenance_mode"),
        FieldPanel("last_confirmed_on"),
    ] + CoverImageMixin.cover_panels  # 轮播封面图（CoverImageMixin，peiligo/cover.py）

    # F-06（IA §10 #7）：promote 面板尾挂「禁止搜索引擎收录」位。
    promote_panels = Page.promote_panels + SeoControlMixin.seo_panels

    # M3.4：搜索索引字段映射（§20.1 表 A 骨架＋表 B 本页差异项）——无
    # StreamField 正文（§10.1），结构化字段即全部可检索面：地点/开放时间
    # （中，CM-21 验收锚点）＋联系方式/补充说明（低）＋指南类别词表；
    # 无标签字段（表 B"—"）。无进索引声明见 §20.3（维护方式/责任方等）。
    search_fields = content_search_fields(
        index.SearchField("location"),
        index.SearchField("opening_hours"),
        index.SearchField("contact", boost=SEARCH_BOOST_LOW),
        index.SearchField("extra_notes", boost=SEARCH_BOOST_LOW),
        index.RelatedFields("category", [index.SearchField("name"), index.FilterField("name")]),
    )

    def clean(self):
        super().clean()
        errors = {}
        clean_content_page(self, errors)
        # §16.1：expire_at 强制空（官方面板位点保留，值层拦截）。
        clean_publish_window(self, errors, EXPIRE_FORBIDDEN)
        if errors:
            raise ValidationError(errors)
