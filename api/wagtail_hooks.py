"""E9 预览出口（docs/api/README.md §3.1 第 2/3 步，B02 实现位）。

- 后台编辑页头「新前端预览」按钮（register_page_header_buttons，仅编辑
  视图＋五类内容页＋change 权限——与后台预览同一权限要求）；
- ``/admin/headless-preview/<id>/`` 铸造端点（register_admin_urls 挂
  wagtailadmin，自动获 require_admin_access 门禁）：签名票据绑定（管理
  会话、用户、页面 pk），``django.core.signing``＋既有 SECRET_KEY（专用
  salt，无新秘密、无新存储载体），有效期 ≤60s；302 到公开域预览保留
  路径 ``/preview/?token=…``（第 3 步，Astro/F04 承接）。兑换端点
  ``/api/v1/preview``（api.views.preview）全程零写入。
"""

from urllib.parse import quote

from django.http import Http404, HttpResponseRedirect
from django.urls import path, reverse
from search.services import SEARCHABLE_PAGE_MODELS
from wagtail import hooks
from wagtail.admin.widgets import Button
from wagtail.models import Page

from .views import PREVIEW_PAGE_PATH, mint_token

BUTTON_LABEL = "新前端预览"
BUTTON_PRIORITY = 80


@hooks.register("register_admin_urls")
def register_preview_exit_url():
    return [path("headless-preview/<int:page_id>/", mint_preview, name="headless_preview")]


@hooks.register("register_page_header_buttons")
def preview_exit_button(page, user, next_url, view_name):
    if view_name != "edit" or not isinstance(page, SEARCHABLE_PAGE_MODELS):
        return
    if not page.permissions_for_user(user).can_edit():
        return
    yield Button(
        BUTTON_LABEL,
        reverse("headless_preview", args=(page.pk,)),
        priority=BUTTON_PRIORITY,
    )


def mint_preview(request, page_id):
    """铸造单跳票据并重定向到同源预览页（§3.1 第 2→3 步）。"""
    page = Page.objects.filter(pk=page_id).first()
    if page is None or not isinstance(page.specific, SEARCHABLE_PAGE_MODELS):
        raise Http404
    if not page.permissions_for_user(request.user).can_edit():
        raise Http404
    if not request.session.session_key:
        request.session.create()
    token = mint_token(request.session.session_key, request.user.pk, page_id)
    return HttpResponseRedirect(f"{PREVIEW_PAGE_PATH}?token={quote(token, safe='')}")
