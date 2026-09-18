"""API v1 端点（E1–E9，ADR-0008；docs/api/README.md §1–§4）。

只读、零写端点；响应与现有 Django 模板渲染行为等价（同一可见性谓词、
同一过滤层、同一排序、同一外链门控）。全部端点经 ``api_view`` 包装：
GET-only（其余 405）、统一错误封装（§2.4）、``Cache-Control: no-store``
（F1，每请求实时计算、无任何缓存层）。

E9 预览兑换（§3.1 第 5 步）镜像 wagtailadmin ``PreviewOnEdit.get`` 的
草稿重建路径（FormState 表单暂存 → 表单类重建 → defer_required →
``save(commit=False)`` 零写入），序列化经 E6 同一投影层＋preview 标记；
任一失败一律 404（不区分原因，防预言机）。
"""

import logging
import uuid
from functools import wraps
from importlib import import_module
from urllib.parse import urlparse

from departments.models import DepartmentContainerPage
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import InterfaceError, OperationalError
from django.http import Http404, JsonResponse
from django.http.request import QueryDict
from django.utils import timezone
from django.utils.translation import gettext
from home.models import (
    SECTIONS,
    SectionPage,
    SiteSettings,
    _active_alert,
    _carousel_entries,
    _featured_entries,
    _latest_notices,
    _upcoming_events,
)
from home.views import _confirm_context
from notices.lifecycle import LIFECYCLE_EXPIRED, LIFECYCLE_LIVE
from search import services
from search.services import (
    SEARCHABLE_PAGE_MODELS,
    SECTION_SLUGS,
    SearchFilters,
    paginate_entries,
    resolve_search_filters,
    resolve_section_filters,
    search_pages,
    section_chips,
)
from wagtail.admin.models import FormState
from wagtail.contrib.sitemaps.sitemap_generator import Sitemap
from wagtail.models import Page, Site

from peiligo.context_processors import _feedback_email

from . import serializers

logger = logging.getLogger(__name__)

JSON_CONTENT_TYPE = "application/json; charset=utf-8"

# E9 票据（§3.1 第 2 步）：复用既有 SECRET_KEY，专用 salt 无新秘密载体；
# 有效期 ≤60s；载荷绑定（管理会话、用户、页面 pk）。
PREVIEW_TOKEN_SALT = "peiligo.api.preview"
PREVIEW_TOKEN_MAX_AGE = 60
# 预览保留路径（冻结 IA：根级子页仅五板块 slug，无路径冲突）。
PREVIEW_PAGE_PATH = "/preview/"

_ERROR_MESSAGES = {
    404: ("not_found", "资源不存在"),
    405: ("method_not_allowed", "仅支持 GET 请求"),
    500: ("server_error", "服务暂时不可用，请稍后重试"),
    503: ("unavailable", "服务暂时不可用，请稍后重试"),
}


def api_error(status):
    code, message = _ERROR_MESSAGES[status]
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def no_store(response):
    response["Cache-Control"] = "no-store"
    return response


def api_view(view):
    """API 端点包装：GET-only、统一错误封装、恒 no-store（§2.1/§2.4/F1）。
    500 只记服务端日志，响应不泄露路径/栈/环境细节。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method != "GET":
            response = api_error(405)
            response["Allow"] = "GET"
            return no_store(response)
        try:
            response = view(request, *args, **kwargs)
        except Http404:
            response = api_error(404)
        except (OperationalError, InterfaceError):
            logger.warning("API 数据库不可用：%s", view.__name__)
            response = api_error(503)
        except Exception:
            logger.exception("API 未预期错误：%s", view.__name__)
            response = api_error(500)
        return no_store(response)

    return wrapper


def mint_token(session_key, user_pk, page_pk):
    """§3.1 第 2 步：铸造签名票据（载荷绑定会话/用户/页面 pk）。"""
    return signing.dumps({"s": session_key, "u": user_pk, "p": page_pk}, salt=PREVIEW_TOKEN_SALT)


# E1：页头/页脚/紧急提示（site_chrome 处理器＋_active_alert 同源）。
@api_view
def chrome(request):
    now = timezone.now()
    return JsonResponse(
        {
            "site_name": settings.WAGTAIL_SITE_NAME,
            "nav_sections": [
                {
                    "slug": section["slug"],
                    "title": section["title"],
                    "url": f"/{section['slug']}/",
                }
                for section in SECTIONS
            ],
            "feedback_email": _feedback_email(request),
            "alert": _active_alert(SiteSettings.for_request(request), now),
        }
    )


# E2：首页数据（HomePage.get_context Phase 8C 同构：轮播/五板块导航/校园快讯）。
@api_view
def home(request):
    now = timezone.now()
    root = Site.find_for_request(request).root_page.specific
    children = {page.slug: page for page in root.get_children().live().type(SectionPage)}
    featured = _featured_entries(now)
    latest = list(_latest_notices())
    upcoming = _upcoming_events(now, children.get("events"))
    return JsonResponse(
        {
            "title": root.title,
            "alert": _active_alert(SiteSettings.for_request(request), now),
            "carousel": [serializers.carousel_entry(entry) for entry in _carousel_entries(root.pk)],
            "sections": [
                {"slug": page.slug, "title": page.title, "url": page.url}
                for page in (
                    children[section["slug"]] for section in SECTIONS if section["slug"] in children
                )
            ],
            "campus_news": [
                serializers.campus_news_entry(page)
                for page in serializers.campus_news_pages(featured, latest, upcoming)
            ],
        }
    )


# E3：板块默认列表（SectionPage.get_context 同构：CURRENT_DEFAULT＋四参数
# 筛选＋20/页宽容分页）。
@api_view
def section_list(request, slug):
    section = SectionPage.objects.live().filter(slug=slug).first()
    if section is None:
        raise Http404
    filters = resolve_section_filters(request.GET, section)
    entries = search_pages(filters)
    page_obj, _ = paginate_entries(entries, request.GET.get("page"))
    return JsonResponse(
        {
            "section": {
                "slug": section.slug,
                "title": section.title,
                "url": section.url,
                "archive_url": f"/{section.slug}/archive/",
            },
            "entries": [serializers.list_entry(page) for page in page_obj.object_list],
            "pagination": serializers.pagination(page_obj),
            "filters": serializers.filters_echo(filters),
        }
    )


# E4：板块历史归档（home.views.section_archive 同构：HISTORICAL 全量不分页）。
@api_view
def section_archive(request, slug):
    if slug not in SECTION_SLUGS:
        raise Http404
    section = SectionPage.objects.live().filter(slug=slug).first()
    if section is None:
        raise Http404
    filters = SearchFilters(section=section, section_from_path=True)
    entries = search_pages(filters, visibility=services.VISIBILITY_HISTORICAL)
    return JsonResponse(
        {
            "section": {
                "slug": section.slug,
                "title": section.title,
                "url": section.url,
            },
            "entries": [serializers.list_entry(page) for page in entries],
            "total": len(entries),
        }
    )


# E5：全站搜索（search.views.search 同构：五参数＋HISTORICAL＋表单态短路）。
@api_view
def search(request):
    filters = resolve_search_filters(request.GET)
    # 无参数（解析后无任何有效维度）＝表单态，不查全量（IA §9.2 #1）。
    results = (
        search_pages(filters, visibility=services.VISIBILITY_HISTORICAL)
        if filters.filter_active
        else []
    )
    page_obj, _ = paginate_entries(results, request.GET.get("page"))
    return JsonResponse(
        {
            "q": filters.q,
            "entries": [serializers.list_entry(page) for page in page_obj.object_list],
            "pagination": serializers.pagination(page_obj),
            "filters": serializers.filters_echo(filters),
            "chips": section_chips(request.GET, filters.section.slug if filters.section else None),
        }
    )


# E6：内容页详情（具名 URL 渲染语义：live 正常、expired 放行带标记、
# S0/S1/S4 404；容器永不渲染）。
@api_view
def page_detail(request, section, dept, slug):
    page = _resolve_content_page(section, dept, slug)
    return JsonResponse(serializers.page_detail_data(page))


def _resolve_content_page(section, dept, slug):
    """路径逐段解析（板块 → 部门容器 → 内容页），镜像 Wagtail 路由口径：
    板块与容器须 live（未发布祖先＝不可达）；叶子经 LifecycleStateMixin
    判定放行 live/expired。"""
    section_page = SectionPage.objects.live().filter(slug=section).first()
    if section_page is None:
        raise Http404
    container = (
        section_page.get_children().type(DepartmentContainerPage).live().filter(slug=dept).first()
    )
    if container is None:
        raise Http404
    page = container.get_children().filter(slug=slug).first()
    if page is None:
        raise Http404
    specific = page.specific
    if not isinstance(specific, SEARCHABLE_PAGE_MODELS):
        raise Http404
    if specific.lifecycle_state not in (LIFECYCLE_LIVE, LIFECYCLE_EXPIRED):
        raise Http404
    return specific


# E7：外链确认页要素（_confirm_context 同源；拒绝态 ok=false，恒 200 不 4xx）。
@api_view
def link_confirm(request):
    context = _confirm_context(request)
    source = context["source_page"]
    return JsonResponse(
        {
            "ok": context["target_ok"],
            "target_domain": context["target_domain"],
            "notice_text": context["notice_text"],
            "source": {"title": source.title, "url": source.url} if source else None,
            "go_href": context["go_url"] or None,
            "problem": context["problem"],
        }
    )


# E8：sitemap 条目（wagtail.contrib.sitemaps 同源：items() 即现状查询）。
@api_view
def sitemap(request):
    entries = []
    for item in Sitemap(request).items():
        for url_info in item.get_sitemap_urls(request):
            entries.append(
                serializers.sitemap_entry(
                    urlparse(url_info["location"]).path, url_info.get("lastmod")
                )
            )
    return JsonResponse({"entries": entries})


def not_found(request):
    """/api/v1/ 空间未匹配路径的统一 404 封装（任意方法，不落 wagtail
    兜底路由的 HTML 404）。"""
    return no_store(api_error(404))


# E9：预览兑换（§3.1 第 5 步；全部失败一律 404，防预言机；零写入）。
@api_view
def preview(request):
    token = request.GET.get("token", "")
    if len(token) < 32:
        raise Http404
    try:
        payload = signing.loads(token, salt=PREVIEW_TOKEN_SALT, max_age=PREVIEW_TOKEN_MAX_AGE)
    except signing.BadSignature:
        raise Http404 from None
    # 绑定会话仍存在且仍认证同一用户（票据兑换请求来自 Astro SSR，无
    # 编辑器 Cookie——按载荷会话键取回会话记录核对认证身份）。
    session = _session_store(payload.get("s"))
    if session.get("_auth_user_id") != str(payload.get("u")):
        raise Http404
    user = get_user_model().objects.filter(pk=payload.get("u")).first()
    page = Page.objects.filter(pk=payload.get("p")).first()
    if user is None or page is None:
        raise Http404
    # 与后台预览同一权限要求（wagtailadmin PreviewOnEdit.get 同款 can_edit）。
    if not page.permissions_for_user(user).can_edit():
        raise Http404
    specific = page.specific
    if not isinstance(specific, SEARCHABLE_PAGE_MODELS):
        raise Http404
    return JsonResponse(serializers.page_detail_data(_rebuild_draft(specific, user), preview=True))


def _session_store(session_key):
    """按键取回会话记录；不存在/已过期时 load() 返回空 dict＝校验失败。"""
    if not session_key:
        raise Http404
    engine = import_module(settings.SESSION_ENGINE)
    return engine.SessionStore(session_key)


def _rebuild_draft(specific, user):
    """草稿只读重建（镜像 wagtailadmin PreviewOnEdit.get 同一表单路径）：
    表单暂存 → 最新修订对象 → 表单类重建 → defer_required 校验 →
    ``save(commit=False)``（cluster 关系仅入内存，零写入）。表单构造与
    PreviewOnEdit.get_form 逐参一致——实例绑定 edit handler（页表单不含
    Page 基类字段）＋parent_page（slug 唯一性校验域）＋title/slug 占位。"""
    obj = specific.get_latest_revision_as_object()
    form_state = (
        FormState.objects.for_preview(user=user, instance=obj, parent_object_id="")
        .order_by("-last_updated_at")
        .first()
    )
    if form_state is None:
        raise Http404
    query_dict = QueryDict(form_state.data)
    if not query_dict.get("title"):
        query_dict = query_dict.copy()
        query_dict["title"] = gettext("Placeholder title")
    if not query_dict.get("slug"):
        query_dict = query_dict.copy()
        query_dict["slug"] = uuid.uuid4()
    form_class = obj.get_edit_handler().get_form_class()
    form = form_class(
        query_dict,
        instance=obj,
        parent_page=obj.get_parent().specific,
        for_user=user,
    )
    form.defer_required_fields()
    if not form.is_valid():
        raise Http404
    form.save(commit=False)
    return form.instance
