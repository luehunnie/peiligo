from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from search import views as search_views
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps import views as sitemap_views
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
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
