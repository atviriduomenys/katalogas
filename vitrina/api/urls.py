from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from vitrina.api.views import CatalogViewSet, DatasetViewSet, CategoryViewSet, LicenceViewSet, \
    DatasetDistributionViewSet, DatasetStructureViewSet, InternalDatasetViewSet, InternalDatasetDistributionViewSet, \
    InternalDatasetStructureViewSet, PartnerApiView, DatasetModelDownloadViewSet
from vitrina.api.views import edp_dcat_ap_rdf

router = DefaultRouter(trailing_slash=False)
router.register(r'catalogs', CatalogViewSet, basename="api-catalog")
router.register(r'categories', CategoryViewSet, basename="api-category")
router.register(r'licences', LicenceViewSet, basename="api-licence")

urlpatterns = [
    path('partner/api/1/', PartnerApiView.with_ui('redoc'), name='partner-api'),
    path('partner/api/1/', include(router.urls)),

    # dataset api urls
    path('partner/api/1/datasets', DatasetViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name="api-dataset"),
    path('partner/api/1/datasets/<int:datasetId>', DatasetViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name="api-single-dataset"),
    path('partner/api/1/datasets/id/<str:internalId>', InternalDatasetViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name="api-single-dataset-internal"),

    # dataset distribution api urls
    path('partner/api/1/datasets/<int:datasetId>/distributions',
         DatasetDistributionViewSet.as_view({
             'get': 'list',
             'post': 'create',
             'put': 'create_with_put'
         }), name="api-distribution"),
    path('partner/api/1/datasets/id/<str:internalId>/distributions',
         InternalDatasetDistributionViewSet.as_view({
             'get': 'list',
             'post': 'create',
             'put': 'create_with_put'
         }), name="api-distribution-internal"),
    path('partner/api/1/datasets/<int:datasetId>/distributions/<int:distributionId>',
         DatasetDistributionViewSet.as_view({
             'get': 'retrieve',
             'patch': 'partial_update',
             'delete': 'destroy'
         }), name="api-single-distribution"),
    path('partner/api/1/datasets/id/<str:internalId>/distributions/<int:distributionId>',
         InternalDatasetDistributionViewSet.as_view({
             'get': 'retrieve',
             'patch': 'partial_update',
             'delete': 'destroy'
         }), name="api-single-distribution-internal"),

    # dataset structure api urls
    path('partner/api/1/datasets/<int:datasetId>/structure',
         DatasetStructureViewSet.as_view({
             'get': 'list',
             'post': 'create'
         }), name="api-structure"),
    path('partner/api/1/datasets/id/<str:internalId>/structure',
         InternalDatasetStructureViewSet.as_view({
             'get': 'list',
             'post': 'create'
         }), name="api-structure-internal"),
    path('partner/api/1/datasets/<int:datasetId>/structure/<int:structureId>',
         DatasetStructureViewSet.as_view({
             'delete': 'destroy'
         }), name="api-single-structure"),
    path('partner/api/1/datasets/id/<str:internalId>/structure/<int:structureId>',
         InternalDatasetStructureViewSet.as_view({
             'delete': 'destroy'
         }), name="api-single-structure-internal"),

    path('partner/api/1/downloads',
         DatasetModelDownloadViewSet.as_view({
             'post': 'create'
         }), name="api-download-stats-internal"),

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
    path('edp/dcat-ap.rdf', edp_dcat_ap_rdf, name="edp-dcat-ap-rdf"),
]
