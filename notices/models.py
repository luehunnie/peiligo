"""通知/文章内容页与受控标签（CONTENT_MODEL §2/§5/§6/§7/§12）。

- ``NoticePage``/``ArticlePage``：两种独立 Page 类型，不混用（PRD §7.2 末句；
  ADR-0005 载体表 #1/#2）；
- ``EventFieldsMixin``：纯抽象 Mixin（models.Model 子类＋Meta.abstract），
  仅本模块内单源定义、仅 Notice/Article 双页继承（§2 类型组织终判）；
- ``Tag``：受控标签词表（taggit 官方 taxonomy 模式，§12 机制 A）。
"""

from departments.forms import ParentContextPageForm
from departments.models import SectionContextMixin, clean_content_page
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.models import ItemBase, TagBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from notices.blocks import CONTENT_BLOCKS
from notices.lifecycle import (
    EXPIRE_OPTIONAL,
    EXPIRE_REQUIRED,
    LifecycleStateMixin,
    clean_publish_window,
)


@register_snippet
class Tag(TagBase):
    """受控标签词表（CONTENT_MODEL §12）：字段＝taggit 内建 name/slug 两枚，
    不新增字段；词表初始为空，由总管理员按需建立（CM-08 权限闸）。"""

    class Meta:
        verbose_name = "受控标签"
        verbose_name_plural = "受控标签"
        ordering = ["name"]

    panels = [FieldPanel("name"), FieldPanel("slug")]


class NoticeTag(ItemBase):
    """NoticePage 的受控标签 through 模型（taggit＋modelcluster 官方模式）。"""

    tag = models.ForeignKey(Tag, related_name="notice_tags", on_delete=models.CASCADE)
    content_object = ParentalKey(
        "notices.NoticePage", related_name="tagged_items", on_delete=models.CASCADE
    )


class ArticleTag(ItemBase):
    """ArticlePage 的受控标签 through 模型。"""

    tag = models.ForeignKey(Tag, related_name="article_tags", on_delete=models.CASCADE)
    content_object = ParentalKey(
        "notices.ArticlePage", related_name="tagged_items", on_delete=models.CASCADE
    )


class ControlledTaggableManager(ClusterTaggableManager):
    """受控标签管理器（§12）：编辑表单渲染为词表多选（表单闸，CM-08）。"""

    def formfield(self, form_class=None, **kwargs):
        from notices.forms import ControlledTagField

        return ControlledTagField(
            label=kwargs.pop("label", None) or "受控标签",
            help_text=kwargs.pop("help_text", "") or None,
        )


def clean_controlled_tags(page, errors):
    """校验闸（§12/CM-08）：所提交标签必须全部已存在于词表，
    未知标签在集群自动创建发生前拦截（ValidationError，非事后治理）。"""
    submitted = list(page.tags.all())
    if not submitted:
        return
    known = set(Tag.objects.values_list("pk", flat=True))
    unknown = [t for t in submitted if t.pk is None or t.pk not in known]
    if unknown:
        names = "、".join(str(t) for t in unknown)
        errors["tags"] = [
            f"以下标签不在受控词表中，请联系总管理员维护：{names}（CONTENT_MODEL §12）"
        ]


# M3.4（CONTENT_MODEL §20.1）：SearchField 权重档位——高＝2（沿基类 title
# 既有值）／中＝缺省不写 boost／低＝0.5。档位语义冻结，具体数值＝后续可
# 微调留痕项；E1（DB fallback）忽略 boost（§20.0 事实 5，§20.2）。
SEARCH_BOOST_HIGH = 2
SEARCH_BOOST_LOW = 0.5

# §20.1 表 B：受控标签 RelatedFields（N/A/M 三页共用同一声明）——
# name 进检索文本（E2/E3）；slug∪name 双通道为 tag 过滤键（§21.2）。
TAG_SEARCH_FIELDS = index.RelatedFields(
    "tags",
    [index.SearchField("name"), index.FilterField("slug"), index.FilterField("name")],
)


def content_search_fields(*extra):
    """五类内容页 search_fields 共同骨架（CONTENT_MODEL §20.1 表 A，冻结）。

    子类定义 ``search_fields`` 即整体遮蔽基类声明（§20.0 事实 2——缺一即
    遮蔽丢失），故表 A 逐项自含再声明：title 检索（boost 沿基类值）＋后台
    选择器补全（事实 9，唯一 Autocomplete 用点）；CURRENT_DEFAULT_SEARCH
    谓词两列 live/expired（§21.5；基类无 expired——事实 1）；板块维度路径
    区间 path（§21.1 section）；默认排序键 first_published_at（§21.6——
    保序旋钮 ``order_by_relevance=False`` 下排序键须 FilterField，事实 6/7）；
    发布部门 name 进检索文本＋slug 为 dept 过滤键。逐页差异项（表 B）由
    各页经 ``extra`` 追加。容器/结构页处置见 §20.1 末段（容器已清空、
    结构页保留基类默认且不入站内搜索对象域）。
    """
    return [
        index.SearchField("title", boost=SEARCH_BOOST_HIGH),
        index.AutocompleteField("title"),
        index.FilterField("live"),
        index.FilterField("expired"),
        index.FilterField("path"),
        index.FilterField("first_published_at"),
        index.RelatedFields("department", [index.SearchField("name"), index.FilterField("slug")]),
        *extra,
    ]


class EventFieldsMixin(models.Model):
    """活动结构化字段（CONTENT_MODEL §2/§7）——纯抽象 Mixin。

    终判（§2）：仅挂 NoticePage/ArticlePage，不建独立活动 Page；
    非法继承（Material/SoftwareTool/Guide/容器/板块）由 §2 文档级断言＋
    评审核对落实。字段位与必填性本文冻结；到期/归档行为语义见 DEFERRED_TO_M3_3。
    """

    event_start_at = models.DateTimeField("开始时间", null=True, blank=True)
    event_end_at = models.DateTimeField("结束时间", null=True, blank=True)
    event_location = models.CharField("活动地点", max_length=200, blank=True)
    event_is_online = models.BooleanField("线上活动", default=False)
    event_registration_url = models.URLField("报名链接", blank=True)

    class Meta:
        abstract = True

    # 事件面板组（§5.3：由 Mixin 注入 content_panels；校园纪事板块下隐藏
    # 该组属表单定制，设计标注留后续实现，clean 已强制板块语义）。
    event_field_panels = [
        FieldPanel("event_start_at"),
        FieldPanel("event_end_at"),
        FieldPanel("event_is_online"),
        FieldPanel("event_location"),
        FieldPanel("event_registration_url"),
    ]
    event_panels = [MultiFieldPanel(event_field_panels, "活动信息（仅校园活动板块填写）")]

    STATUS_UPCOMING = "即将开始"
    STATUS_ONGOING = "进行中"
    STATUS_ENDED = "已结束"

    @property
    def event_status(self):
        """活动状态三态（§7.1/CM-03）：按当前时间对比起止的纯计算——
        now < start → 即将开始；start ≤ now ≤ end → 进行中（闭区间）；
        now > end → 已结束。起止未填（校园纪事板块）时无状态，返回 None。"""
        if self.event_start_at is None or self.event_end_at is None:
            return None
        now = timezone.now()
        if now < self.event_start_at:
            return self.STATUS_UPCOMING
        if now > self.event_end_at:
            return self.STATUS_ENDED
        return self.STATUS_ONGOING

    def clean_event_fields(self, section_slug, errors):
        """活动字段 clean（§7.2 适用规则，板块决定）：
        events 板块起止必填、线下必填地点；chronicle 板块五字段强制全空。
        成对校验（§7.1）：与开始同时填/同时空，且结束 ≥ 开始（相等合法）。"""
        start, end = self.event_start_at, self.event_end_at
        if section_slug == "events":
            if start is None:
                errors["event_start_at"] = ["校园活动板块下活动必须填写开始时间"]
            elif end is None:
                errors["event_end_at"] = ["校园活动板块下活动必须填写结束时间"]
            if not self.event_is_online and not self.event_location:
                errors["event_location"] = ["线下活动必须填写活动地点"]
        else:
            # 校园纪事板块（挂本 Mixin 的两类页面仅允许 chronicle/events）：
            # 双保险防误填——任一活动字段已填即报错（§7.2）。
            if start is not None:
                errors["event_start_at"] = ["校园纪事板块内容不是活动，活动字段须留空"]
            if end is not None:
                errors["event_end_at"] = ["校园纪事板块内容不是活动，活动字段须留空"]
            if self.event_location:
                errors["event_location"] = ["校园纪事板块内容不是活动，活动字段须留空"]
            if self.event_is_online:
                errors["event_is_online"] = ["校园纪事板块内容不是活动，活动字段须留空"]
            if self.event_registration_url:
                errors["event_registration_url"] = ["校园纪事板块内容不是活动，活动字段须留空"]
        if start is not None and end is not None and end < start:
            errors["event_end_at"] = ["活动结束时间不得早于开始时间（相等合法）"]


def _notice_article_panels():
    """Notice/Article 共享 panels 骨架（§5.3 顺序；两类型仅有效期必填性差异）。"""
    return [
        FieldPanel("department"),
        FieldPanel("summary"),
        FieldPanel("body"),
        FieldPanel("image"),
        FieldPanel("attachments"),
        FieldPanel("external_url"),
        FieldPanel("tags"),
    ]


class NoticePage(EventFieldsMixin, SectionContextMixin, LifecycleStateMixin, Page):
    """通知页（CONTENT_MODEL §5；PRD §7.1）。

    与 ArticlePage 字段集同构，唯一差异：有效期必填（CM-01，clean 强制）；
    生命周期五状态零字段纯推导（§14，LifecycleStateMixin）。
    """

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "通知页"
        verbose_name_plural = "通知页"

    parent_page_types = ["departments.DepartmentContainerPage"]  # 唯一父级（§1.4）
    subpage_types = []  # 叶子（§1.4：内容页均为叶子，树深固定四层）
    ALLOWED_SECTIONS = {"chronicle", "events"}  # §1.4 板块级限制
    # 提交流程父级注入（departments.forms）——clean() 创建期板块/部门校验用。
    base_form_class = ParentContextPageForm

    summary = models.TextField("摘要")
    body = StreamField(CONTENT_BLOCKS, min_num=1, use_json_field=True, verbose_name="正文")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        verbose_name="发布部门",
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="图片",
    )
    attachments = ParentalManyToManyField(
        "wagtaildocs.Document",
        blank=True,
        verbose_name="附件",
    )
    external_url = models.URLField("外部链接", blank=True)
    tags = ControlledTaggableManager(through=NoticeTag, blank=True)

    content_panels = Page.content_panels + _notice_article_panels() + EventFieldsMixin.event_panels
    # promote_panels/settings_panels 保持官方默认（§5.3：含 PublishingPanel
    # 的 go_live_at/expire_at 位点；行为语义 DEFERRED_TO_M3_3）。

    # M3.4：搜索索引字段映射（§20.1 表 A 骨架＋表 B 本页差异项——摘要/
    # 正文（中）＋活动地点（低，EventFieldsMixin 结构化贡献）＋受控标签）。
    search_fields = content_search_fields(
        index.SearchField("summary"),
        index.SearchField("body"),
        index.SearchField("event_location", boost=SEARCH_BOOST_LOW),
        TAG_SEARCH_FIELDS,
    )

    def clean(self):
        super().clean()
        errors = {}
        section = clean_content_page(self, errors)
        # §16.1/§16.2：有效期必填（CM-01）＋须晚于当前时刻（发布未来性）。
        clean_publish_window(self, errors, EXPIRE_REQUIRED)
        self.clean_event_fields(section, errors)
        clean_controlled_tags(self, errors)
        if errors:
            raise ValidationError(errors)


class ArticlePage(EventFieldsMixin, SectionContextMixin, LifecycleStateMixin, Page):
    """文章页（CONTENT_MODEL §6；PRD §7.2）。

    与 NoticePage 字段集完全同构，唯一差异：有效期可选
    （expire_at 保持可空，"不默认设置下线时间"，CM-01 仅约束通知；
    如填写则须未来，§16.2）；生命周期五状态零字段纯推导（§14）。
    """

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "文章页"
        verbose_name_plural = "文章页"

    parent_page_types = ["departments.DepartmentContainerPage"]
    subpage_types = []
    ALLOWED_SECTIONS = {"chronicle", "events"}
    base_form_class = ParentContextPageForm

    summary = models.TextField("摘要")
    body = StreamField(CONTENT_BLOCKS, min_num=1, use_json_field=True, verbose_name="正文")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        verbose_name="发布部门",
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="图片",
    )
    attachments = ParentalManyToManyField(
        "wagtaildocs.Document",
        blank=True,
        verbose_name="附件",
    )
    external_url = models.URLField("外部链接", blank=True)
    tags = ControlledTaggableManager(through=ArticleTag, blank=True)

    content_panels = Page.content_panels + _notice_article_panels() + EventFieldsMixin.event_panels

    # M3.4：搜索索引字段映射（§20.1 表 A 骨架＋表 B 本页差异项）——与
    # NoticePage 差异集相同（§5/§6 字段集同构）。
    search_fields = content_search_fields(
        index.SearchField("summary"),
        index.SearchField("body"),
        index.SearchField("event_location", boost=SEARCH_BOOST_LOW),
        TAG_SEARCH_FIELDS,
    )

    def clean(self):
        super().clean()
        errors = {}
        section = clean_content_page(self, errors)
        # §16.2：expire_at 可空；如填写则须未来（"不默认设置下线时间"）。
        clean_publish_window(self, errors, EXPIRE_OPTIONAL)
        self.clean_event_fields(section, errors)
        clean_controlled_tags(self, errors)
        if errors:
            raise ValidationError(errors)
