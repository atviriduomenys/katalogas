from django.urls import path, include
from rest_framework.routers import DefaultRouter

from vitrina.api.services import get_partner_schema_view
from vitrina.api.views import CatalogViewSet, CategoryViewSet, LicenceViewSet

router = DefaultRouter()
router.register(r'catalogs', CatalogViewSet, basename="catalog")
router.register(r'categories', CategoryViewSet, basename="category")
router.register(r'licences', LicenceViewSet, basename="licence")

urlpatterns = [
    path('partner/api/1/', get_partner_schema_view().with_ui('redoc'), name='partner-api'),
    path('partner/api/1/', include(router.urls)),

    # @RequestMapping("/api")
    # @GetMapping("/partner/api/1")
    # @GetMapping("partner/api/1/licences")
    # @GetMapping("/public/api/1")
    # @GetMapping("/edp/api/1")

    # @RequestMapping("/edp")
    # @RequestMapping("/edp/refresh")
    # @RequestMapping("/edp/dcat-ap.rdf")

    # @GetMapping("/sparql")

    # @RequestMapping("/rdf")
    # @PostMapping("/rdf/search")
]
