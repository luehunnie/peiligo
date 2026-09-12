"""全站搜索页（/search/，自定义视图不入页面树——ADR-0005 载体表 #5 先例）。

M3.4（CONTENT_MODEL §21）：五参数规格 q/section/dept/type/tag（IA §9），
非法值视同未提供（200 回退全量）；状态全在 URL（GET 可分享/可刷新）；
无参数＝搜索表单态（IA §9.2 #1）；noindex+canonical 见模板（IA §10 #7）。
查询与过滤全部委托 ``services``（与板块页共用同一过滤层）。
"""

from django.template.response import TemplateResponse

from search import services


def search(request):
    filters = services.resolve_search_filters(request.GET)
    # 无参数（解析后无任何有效维度）＝表单态，不查全量（IA §9.2 #1）。
    # 入口绑定（M5.2 §7/§7.1）：搜索入口＝ARCHIVE-SEARCH（HISTORICAL 同
    # 谓词）——expired 默认命中，结果条目经内容卡带「已过期」标注；无
    # 用户开关（§21.4 零新增公开参数）。
    results = (
        services.search_pages(filters, visibility=services.VISIBILITY_HISTORICAL)
        if filters.filter_active
        else []
    )
    # Phase 8B：共享分页（search_results 键名与既有契约不变，值＝当前页
    # 条目）；翻页链接保留全部筛选参数（querystring 已剔除 page）。
    page_obj, page_links = services.paginate_entries(results, request.GET.get("page"))
    querystring = _querystring_without_page(request.GET)
    return TemplateResponse(
        request,
        "search/search.html",
        {
            "search_query": filters.q,
            "search_filters": filters,
            "search_results": page_obj.object_list,
            "filter_active": filters.filter_active,
            "page_obj": page_obj,
            "page_links": page_links,
            "querystring": querystring,
            "total_results": page_obj.paginator.count,
            "section_chips": services.section_chips(
                request.GET, filters.section.slug if filters.section else None
            ),
            # 高亮词＝原始解析后的 q（escape-safe 过滤器内部自行转义）。
            "highlight_q": filters.q,
        },
    )


def _querystring_without_page(params):
    """剔除 page 后的查询串（翻页保留 q/section/dept/type/tag）。"""
    restored = params.copy()
    restored.pop("page", None)
    return restored.urlencode()
