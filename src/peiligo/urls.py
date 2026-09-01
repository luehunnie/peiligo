from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from home import views as home_views
from home.models import SECTIONS
from search import views as search_views
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps import views as sitemap_views
from wagtail.documents import urls as wagtaildocs_urls

# M5.2（§6.1/§6.3 B 阶段裁定）：五板块历史归档视图＝/<板块>/archive/，
# 自定义视图不入页面树（ADR-0005 载体表 #5 先例）；正则封闭五冻结 slug，
# 不遮蔽任何 Wagtail 子树路径。
_SECTION_ARCHIVE_SLUGS = "|".join(section["slug"] for section in SECTIONS)

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    # F-09：容器健康检查探针（存活/就绪；最小 JSON，不泄露环境细节），
    # 须在 wagtail 兜底路由之前。
    path("healthz/", home_views.healthz, name="healthz"),
    path("readyz/", home_views.readyz, name="readyz"),
    # F-03（CM §11.4/PRD §7.5）：外链统一确认页＋「继续访问」端点；自定义
    # 视图不入页面树（ADR-0005 #5 先例）→ 不进 sitemap；整页恒 noindex。
    path("link-confirm/", home_views.link_confirm, name="link-confirm"),
    path("link-confirm/go/", home_views.link_confirm_go, name="link-confirm-go"),
    # F-06（IA §10）：robots.txt——管理面与外链确认页禁抓；/search/ 不在
    # Disallow（noindex 是收录语义，robots Disallow 反致 meta 读不到）。
    # Sitemap 取请求 Host 拼绝对地址；自定义视图不入页面树（ADR-0005 #5）。
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots-txt",
    ),
    re_path(
        rf"^({_SECTION_ARCHIVE_SLUGS})/archive/$",
        home_views.section_archive,
        name="section-archive",
    ),
    # M2.2（IA §10 #1–#3）：sitemap.xml；容器排除=DepartmentContainerPage.
    # get_sitemap_urls 返回空（IA-03），query 状态页不在页面树、天然不进入。
    path("sitemap.xml", sitemap_views.sitemap, name="wagtail-sitemap"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
