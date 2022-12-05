from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from vitrina.api.services import get_partner_schema_view
from vitrina.api.views import CatalogViewSet, CategoryViewSet, LicenceViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'catalogs', CatalogViewSet, basename="api-catalog")
router.register(r'categories', CategoryViewSet, basename="api-category")
router.register(r'licences', LicenceViewSet, basename="api-licence")

urlpatterns = [
    path('partner/api/1/', get_partner_schema_view().with_ui('redoc'), name='partner-api'),
    path('partner/api/1/', include(router.urls)),

    # @RequestMapping("/api")
    # @GetMapping("/partner/api/1")
    # @GetMapping("partner/api/1/licences")
    # @GetMapping("/public/api/1")
    path('public/api/1/', TemplateView.as_view(template_name="vitrina/api/public_api.html"), name="public-api"),
    # @GetMapping("/edp/api/1")

    # @RequestMapping("/edp")
    # @RequestMapping("/edp/refresh")
    # @RequestMapping("/edp/dcat-ap.rdf")

    # @GetMapping("/sparql")

    # @RequestMapping("/rdf")
    # @PostMapping("/rdf/search")
]
