from django.urls import path, re_path

from . import views

# E1–E9（ADR-0008 §1）；经 src/peiligo/urls.py 以 path("api/v1/", include)
# 挂载在 wagtail 兜底路由之前。末位 catch-all 兜住 /api/v1/ 空间的其余
# 路径＝统一 404 封装（不落进 wagtail 页面路由的 HTML 404）。
urlpatterns = [
    path("chrome", views.chrome),
    path("home", views.home),
    path("sections/<slug:slug>", views.section_list),
    path("sections/<slug:slug>/archive", views.section_archive),
    path("search", views.search),
    path("pages/<slug:section>/<slug:dept>/<slug:slug>", views.page_detail),
    path("link-confirm", views.link_confirm),
    path("sitemap", views.sitemap),
    path("preview", views.preview),
    re_path(r"^", views.not_found),
]
