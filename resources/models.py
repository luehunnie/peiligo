"""学习资料页/软件工具页与资料侧受控词表（CONTENT_MODEL §8/§9/§13.2）。

V1 明确不做课程/教师/学期课程库（PRD §7.4 末句）；软件工具不托管安装包
（PRD §7.5 原则，§9.1 无字段声明）。
"""

from departments.forms import ParentContextPageForm
from departments.models import SectionContextMixin, clean_content_page
from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from notices.blocks import CONTENT_BLOCKS, SOFTWARE_TOOL_BLOCKS
from notices.lifecycle import EXPIRE_FORBIDDEN, LifecycleStateMixin, clean_publish_window
from notices.models import (
    SEARCH_BOOST_LOW,
    TAG_SEARCH_FIELDS,
    ControlledTaggableManager,
    Tag,
    clean_controlled_tags,
    content_search_fields,
)
from taggit.models import ItemBase
from wagtail.admin.panels import FieldPanel, TitleFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from peiligo.cover import CoverImageMixin
from peiligo.link_validation import validate_external_url
from peiligo.seo import SeoControlMixin


class _ControlledVocabulary(models.Model):
    """受控类别词表同构骨架（§13.2：四词表字段仅两枚——名称/排序）。

    词表由总管理员维护；被引用（FK PROTECT/M2M）时删除受保护
    （删除政策 DEFERRED_TO_M3_3）。
    """

    name = models.CharField("名称", max_length=100, unique=True)
    sort_order = models.IntegerField("排序", default=0)

    panels = [FieldPanel("name"), FieldPanel("sort_order")]

    class Meta:
        abstract = True
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


@register_snippet
class Discipline(_ControlledVocabulary):
    """学科·专业方向词表（§13.2；消费形态＝MaterialPage 单 FK）。"""

    class Meta(_ControlledVocabulary.Meta):
        verbose_name = "学科·专业方向"
        verbose_name_plural = "学科·专业方向"


@register_snippet
class MaterialType(_ControlledVocabulary):
    """资料类型词表（§13.2；消费形态＝MaterialPage 单 FK）。"""

    class Meta(_ControlledVocabulary.Meta):
        verbose_name = "资料类型"
        verbose_name_plural = "资料类型"


@register_snippet
class Platform(_ControlledVocabulary):
    """适用平台词表（§13.2；消费形态＝SoftwareToolPage M2M）。"""

    class Meta(_ControlledVocabulary.Meta):
        verbose_name = "适用平台"
        verbose_name_plural = "适用平台"


class MaterialTag(ItemBase):
    """MaterialPage 的受控标签 through 模型（§12：仅词表内标签）。"""

    tag = models.ForeignKey(Tag, related_name="material_tags", on_delete=models.CASCADE)
    content_object = ParentalKey(
        "resources.MaterialPage", related_name="tagged_items", on_delete=models.CASCADE
    )


class MaterialPage(
    SectionContextMixin, LifecycleStateMixin, CoverImageMixin, SeoControlMixin, Page
):
    """学习资料页（CONTENT_MODEL §8；PRD §7.4）。

    受控三维度＝学科（FK）/资料类型（FK）/关键词标签（词表多值）；
    无专属图片字段、无有效期字段（§8.1 无字段声明）；expire_at clean
    强制空（§16.1——常青内容退场走 E8 手动下线）；生命周期五状态零
    字段纯推导（§14）。
    """

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "学习资料页"
        verbose_name_plural = "学习资料页"

    parent_page_types = ["departments.DepartmentContainerPage"]  # 唯一父级（§1.4）
    subpage_types = []  # 叶子（§1.4）
    ALLOWED_SECTIONS = {"materials"}  # §1.4 板块级限制
    base_form_class = ParentContextPageForm

    summary = models.TextField("摘要")
    body = StreamField(CONTENT_BLOCKS, min_num=1, use_json_field=True, verbose_name="正文")
    discipline = models.ForeignKey(
        Discipline, on_delete=models.PROTECT, verbose_name="学科·专业方向"
    )
    material_type = models.ForeignKey(
        MaterialType, on_delete=models.PROTECT, verbose_name="资料类型"
    )
    external_url = models.URLField("外部链接", blank=True, validators=[validate_external_url])
    attachments = ParentalManyToManyField("wagtaildocs.Document", blank=True, verbose_name="附件")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        verbose_name="发布部门",
    )
    tags = ControlledTaggableManager(through=MaterialTag, blank=True)

    # panels 顺序＝§8.2 冻结行序。
    content_panels = [
        FieldPanel("title"),
        FieldPanel("department"),
        FieldPanel("discipline"),
        FieldPanel("material_type"),
        FieldPanel("summary"),
        FieldPanel("body"),
        FieldPanel("external_url"),
        FieldPanel("attachments"),
        FieldPanel("tags"),
    ] + CoverImageMixin.cover_panels  # 轮播封面图（CoverImageMixin，peiligo/cover.py）

    # F-06（IA §10 #7）：promote 面板尾挂「禁止搜索引擎收录」位。
    promote_panels = Page.promote_panels + SeoControlMixin.seo_panels

    # M3.4：搜索索引字段映射（§20.1 表 A 骨架＋表 B 本页差异项——摘要/
    # 正文（中）＋受控标签＋学科/资料类型两词表；词表无 slug，过滤键=name）。
    search_fields = content_search_fields(
        index.SearchField("summary"),
        index.SearchField("body"),
        TAG_SEARCH_FIELDS,
        index.RelatedFields("discipline", [index.SearchField("name"), index.FilterField("name")]),
        index.RelatedFields(
            "material_type", [index.SearchField("name"), index.FilterField("name")]
        ),
    )

    def clean(self):
        super().clean()
        errors = {}
        clean_content_page(self, errors)
        # §16.1：expire_at 强制空（官方面板位点保留，值层拦截）。
        clean_publish_window(self, errors, EXPIRE_FORBIDDEN)
        clean_controlled_tags(self, errors)
        if errors:
            raise ValidationError(errors)


class SoftwareToolPage(
    SectionContextMixin, LifecycleStateMixin, CoverImageMixin, SeoControlMixin, Page
):
    """软件与工具页（CONTENT_MODEL §9；PRD §7.5"每条内容至少包含"六项）。

    网站不直接托管软件安装包——无附件字段且正文白名单不含附件块
    （SOFTWARE_TOOL_BLOCKS＝§11 全集减附件块）；无摘要/图片字段（§9.1）；
    expire_at clean 强制空（§16.1）；生命周期五状态零字段纯推导（§14）。
    """

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "软件与工具页"
        verbose_name_plural = "软件与工具页"

    parent_page_types = ["departments.DepartmentContainerPage"]
    subpage_types = []
    ALLOWED_SECTIONS = {"software"}
    base_form_class = ParentContextPageForm

    body = StreamField(SOFTWARE_TOOL_BLOCKS, min_num=1, use_json_field=True, verbose_name="正文")
    platforms = ParentalManyToManyField(Platform, blank=False, verbose_name="适用平台")
    source_url = models.URLField("来源链接或第三方网盘链接", validators=[validate_external_url])
    license_note = models.TextField("授权或费用说明")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        verbose_name="发布部门",
    )

    # panels 顺序＝§9.2 冻结行序；标题界面标签定制"软件或工具名称"（§9.1，
    # 映射不另设字段）。
    content_panels = [
        TitleFieldPanel("title", heading="软件或工具名称"),
        FieldPanel("department"),
        FieldPanel("platforms"),
        FieldPanel("body"),
        FieldPanel("source_url"),
        FieldPanel("license_note"),
    ] + CoverImageMixin.cover_panels  # 轮播封面图（CoverImageMixin，peiligo/cover.py）

    # F-06（IA §10 #7）：promote 面板尾挂「禁止搜索引擎收录」位。
    promote_panels = Page.promote_panels + SeoControlMixin.seo_panels

    # M3.4：搜索索引字段映射（§20.1 表 A 骨架＋表 B 本页差异项）——无摘要
    # 字段（§9.1）；正文（中）＋授权说明（低，"免费/正版授权"类查询目标）
    # ＋适用平台词表；无标签字段（表 B"—"）。
    search_fields = content_search_fields(
        index.SearchField("body"),
        index.SearchField("license_note", boost=SEARCH_BOOST_LOW),
        index.RelatedFields("platforms", [index.SearchField("name"), index.FilterField("name")]),
    )

    def clean(self):
        super().clean()
        errors = {}
        clean_content_page(self, errors)
        # §9.2：platforms ≥1。blank=False 已在表单字段层拦截（必填）；
        # 本处为模型级兜底，仅对可判定的状态取值——cluster 内存值已就位
        # （模型直建：page.platforms = [...]）或已保存（编辑/树内校验，读库）。
        # 创建表单校验期跳过：Django construct_instance 不处理 many_to_many
        # （回填发生在 save_cluster_m2m），此期 platforms.all() 恒空，
        # 若不跳过会把合法提交误判为空（时序亲证：Django forms/models.py
        # construct_instance 仅遍历 _meta.fields；modelcluster deferring
        # manager 对未保存实例返回空）。
        platforms_known = "platforms" in getattr(self, "_cluster_related_objects", {})
        if (platforms_known or self.pk) and not list(self.platforms.all()):
            errors["platforms"] = ["适用平台至少选择一项（CONTENT_MODEL §9.2）"]
        # §16.1：expire_at 强制空（官方面板位点保留，值层拦截）。
        clean_publish_window(self, errors, EXPIRE_FORBIDDEN)
        if errors:
            raise ValidationError(errors)
