"""vitrina URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views.i18n import JavaScriptCatalog
from django.contrib.sitemaps import views


from vitrina import settings
from vitrina.views import home, version_view, csp_report_view
from vitrina.orgs.admin import site
from django.views.generic import TemplateView
from vitrina.sitemaps import DatasetSitemap, RootSitemap, MoreViewSitemap

sitemaps = {
    "root": RootSitemap,
    "datasets": DatasetSitemap,
    "more": MoreViewSitemap,
}

urlpatterns = [
    path("", home, name="home"),
    path("", include("vitrina.api.urls")),
    path("", include("vitrina.requests.urls")),
    path("", include("vitrina.tasks.urls")),
    path("", include("vitrina.projects.urls")),
    path("", include("vitrina.orgs.urls")),
    path("", include("vitrina.structure.urls")),
    path("", include("vitrina.likes.urls")),
    path("", include("vitrina.messages.urls")),
    path("", include("vitrina.plans.urls")),
    path("", include("vitrina.resources.urls")),
    path("", include("vitrina.catalogs.urls")),
    path("", include("vitrina.users.urls")),
    path("", include("vitrina.datasets.urls")),
    path("", include("vitrina.comments.urls")),
    path("", include("vitrina.classifiers.urls")),
    path("", include("vitrina.cms.urls")),
    path("", include("vitrina.translate.urls")),
    path("", include("vitrina.statistics.urls")),
    path("", include("vitrina.uapi.urls")),
    path("", include("vitrina.smart_contracts.urls")),
    path("", include("vitrina.dcat.urls")),
    path("admin/", admin.site.urls),
    path("coordinator-admin/", site.urls),
    path("taggit-autosuggest/", include("taggit_autosuggest.urls")),
    path("select2/", include("django_select2.urls")),
    path("hitcount/", include("hitcount.urls", namespace="hitcount")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("vitrina.viisp.urls")),
    path("_version/", version_view, name="version"),
    path("csp-report/", csp_report_view, name="csp-report"),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path(
        "sitemap.xml",
        views.index,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.index",
    ),
    path(
        "sitemap-<section>.xml",
        views.sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.INTERNAL_MEDIA_URL, document_root=settings.INTERNAL_MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    path("", include("cms.urls")),
]

handler400 = "vitrina.status_codes_views.handler400"
handler403 = "vitrina.status_codes_views.handler403"
handler404 = "vitrina.status_codes_views.handler404"
handler500 = "vitrina.status_codes_views.handler500"
