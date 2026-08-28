"""M5.2 板块历史归档视图（PUBLISH_ARCHIVE_SCHEDULING §6.1；MB8–MB9）。

五板块各一「历史归档」视图，URL＝``/<板块>/archive/``（B 阶段裁定：自
定义视图不入页面树，ADR-0005 载体表 #5 先例；仅五冻结 slug，不遮蔽任何
Wagtail 子树）。查询与合并委托 ``search.services`` 同一过滤层（§21.1 双
载体的第三消费位），仅可见性谓词不同（HISTORICAL，§6.1）；expired 条目
经内容卡带「已过期」徽标，live 与 expired 同序混排无降权（§6.1 默认排序
``-first_published_at``）。
"""

from django.http import Http404
from django.template.response import TemplateResponse
from search import services
from search.services import SearchFilters

from .models import SectionPage


def section_archive(request, section_slug):
    """板块历史归档（§6.1）：HISTORICAL ∩ 板块子树，发布时间倒序。

    板块对象域＝§1.4 树位置推导（经 ``path__startswith`` 路径区间承载，
    与板块默认列表同口径）；查询参数不生效（归档视图非 §21 载体，§21.4
    零新增公开参数）；未知板块 slug＝404（URL 正则已封闭五值，此处兜底）。
    """
    if section_slug not in services.SECTION_SLUGS:
        raise Http404
    section = SectionPage.objects.live().filter(slug=section_slug).first()
    if section is None:
        raise Http404
    filters = SearchFilters(section=section, section_from_path=True)
    entries = services.search_pages(filters, visibility=services.VISIBILITY_HISTORICAL)
    return TemplateResponse(
        request,
        "home/section_archive.html",
        {"section": section, "archive_entries": entries},
    )
