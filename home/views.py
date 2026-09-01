"""自定义前台视图：M5.2 板块历史归档（PUBLISH_ARCHIVE_SCHEDULING §6.1；
MB8–MB9）与 F-03 外链统一确认跳转页（PRD §7.5）。

五板块各一「历史归档」视图，URL＝``/<板块>/archive/``（B 阶段裁定：自
定义视图不入页面树，ADR-0005 载体表 #5 先例；仅五冻结 slug，不遮蔽任何
Wagtail 子树）。查询与合并委托 ``search.services`` 同一过滤层（§21.1 双
载体的第三消费位），仅可见性谓词不同（HISTORICAL，§6.1）；expired 条目
经内容卡带「已过期」徽标，live 与 expired 同序混排无降权（§6.1 默认排序
``-first_published_at``）。
"""

from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.db import connection
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from search import services
from search.services import SearchFilters
from wagtail.models import Page

from peiligo.link_validation import (
    display_external_url,
    external_url_domain,
    validate_external_url,
)

from .models import SectionPage, SiteSettings


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


# F-03（PRD §7.5 / CM §11.4 / SECURITY_BASELINE §10-7·SB-06·SEC-21/22）：
# 外链统一确认跳转页。四要素＝目标域名、来源、发布/最后更新时间、第三方
# 内容可能变化的声明（无需强制勾选，PRD §7.5）；无任何自动跳转（无 meta
# refresh、无 JS、无 302——确认页与 go 端点分离）。「继续访问」落地端点
# 对目标做与字段层相同的 SB §10-7 校验后才 302（输出层二次校验防库内
# 历史脏数据）；非法目标＝渲染拒绝提示，绝不跳转（SEC-22 白名单语义）。
# 自定义视图不入页面树（ADR-0005 #5 先例）→ 不进 sitemap；整页恒 noindex。
DEFAULT_REDIRECT_NOTICE = (
    "该链接指向校外第三方网站，第三方内容可能随时间发生变化，请以目标网站当前内容为准。"
)


def _confirm_context(request):
    """确认页共享上下文：目标输出层校验＋四要素解析。"""
    raw = request.GET.get("url", "")
    try:
        target = validate_external_url(raw)
        problem = ""
    except ValidationError as error:
        target, problem = "", "；".join(error.messages)
    source_page = None
    from_id = request.GET.get("from", "")
    if from_id.isdigit():
        # R 审查 M3：只引用前台可见页（live∧未到期＝CURRENT_DEFAULT 谓词）——
        # 否则匿名者可借 from 枚举 pk 读到草稿/未发布页标题（可见性边界泄漏）。
        source_page = (
            Page.objects.filter(pk=int(from_id))
            .live()
            .filter(expired=False)
            .only("id", "title", "last_published_at")
            .first()
        )
    notice_text = SiteSettings.for_request(request).redirect_notice_text.strip()
    return {
        "target": raw,
        "target_ok": bool(target),
        "target_display": display_external_url(target) if target else "",
        "target_domain": external_url_domain(target) if target else "",
        "problem": problem,
        "source_page": source_page,
        "notice_text": notice_text or DEFAULT_REDIRECT_NOTICE,
        "go_url": f"{reverse('link-confirm-go')}?url={quote(target, safe='')}" if target else "",
    }


def link_confirm(request):
    """外链统一确认页（PRD §7.5 四要素；CM §11.4；SEC-21）。"""
    return TemplateResponse(request, "home/link_confirm.html", _confirm_context(request))


def link_confirm_go(request):
    """「继续访问」端点：目标二次校验通过后才 302（SB §10-7 校验位置条）；
    非法目标复用确认页拒绝态，不产生跳转（SEC-22）。"""
    try:
        target = validate_external_url(request.GET.get("url", ""))
    except ValidationError:
        return link_confirm(request)
    return HttpResponseRedirect(target)


# F-09（容器健康检查基线）：探针端点挂在 wagtail 兜底路由之前
# （urls.py）。口径：只回答「活/不活、可不可服务」，不泄露 DB URL/
# 路径/版本/栈回溯——响应体恒为最小 JSON；探针失败也不带任何环境
# 细节（503＋unavailable 一词）。
@never_cache
def healthz(request):
    """存活探针：进程在即 200，不触数据库（liveness）。"""
    return JsonResponse({"status": "ok"})


@never_cache
def readyz(request):
    """就绪探针：数据库可应答才 200，否则 503（readiness）。"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
