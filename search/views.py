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
    results = services.search_pages(filters) if filters.filter_active else []
    return TemplateResponse(
        request,
        "search/search.html",
        {
            "search_query": filters.q,
            "search_filters": filters,
            "search_results": results,
            "filter_active": filters.filter_active,
        },
    )
