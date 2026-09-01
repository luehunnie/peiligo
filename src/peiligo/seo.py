"""F-06（IA §10 #7 / SB-07）：逐内容页「禁止收录」开关——SEO 缺口收口。

五类内容页（通知/文章/资料/软件工具/指南）经本抽象 Mixin 获得同一
``noindex`` 字段与两处消费位：

- 前台渲染：base.html 全局 ``head_robots`` 位点读 ``page.noindex``（无
  此字段的页面——首页/板块/容器/自定义视图——模板属性查找静默为假，
  不输出 meta，行为与既有 request.GET 全局 noindex 位点共存）；
- sitemap：``get_sitemap_urls`` 覆写，noindex 页不入 sitemap.xml。

缺省 ``False``＝默认可收录（IA §10 #7 冻结缺省）；外链确认页的整页恒
noindex 已由 F-03 独立位点（模板覆写 block）承载，不经本字段。
"""

from django.db import models
from wagtail.admin.panels import FieldPanel


class SeoControlMixin(models.Model):
    """逐内容页 noindex 开关（抽象 Mixin，仅挂 §1.2 五类内容页）。"""

    noindex = models.BooleanField(
        "禁止搜索引擎收录",
        default=False,
        help_text="勾选后本页输出 noindex 且不进入 sitemap.xml（IA §10 #7）",
    )

    seo_panels = [FieldPanel("noindex")]

    class Meta:
        abstract = True

    def get_sitemap_urls(self, request=None):
        """noindex 页不入 sitemap（其余口径沿官方：live 页含 lastmod）。"""
        if self.noindex:
            return []
        return super().get_sitemap_urls(request)
