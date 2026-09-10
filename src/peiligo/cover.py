"""五类内容页统一轮播封面图（首页轮播 Phase 2 冻结决策；与 seo.py 同风格）。

抽象 Mixin 仅挂五类内容页（CONTENT_MODEL §1.2）：``cover_image`` 是首页
轮播位（home.CarouselItem）引用站内内容时的封面单一来源——轮播项不重复
配置站内标题与图片，直接取目标内容页封面（Phase 2 冻结决策 5）。

- nullable/blank、SET_NULL：封面图删除仅置空，页面本体保留；
- ``related_name="+"``：不建 Image → Page 反向关系；
- 推荐尺寸 1600×600（8:3）＝help_text 软提示，无比例/尺寸硬校验；
- 与 NoticePage/ArticlePage 既有 ``image``（正文插图）语义独立共存，
  两者可同时存在（Phase 2 冻结决策 14）。
"""

from django.db import models
from wagtail.admin.panels import FieldPanel


class CoverImageMixin(models.Model):
    """五类内容页轮播封面图（抽象 Mixin）。"""

    cover_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="轮播封面图",
        help_text="推荐尺寸 1600×600（8:3）",
    )

    cover_panels = [FieldPanel("cover_image")]

    class Meta:
        abstract = True
