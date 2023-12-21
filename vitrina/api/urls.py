from django.urls import include, path
from django.views.generic import TemplateView

from allauth.account.views import confirm_email, email_verification_sent
from rest_framework.routers import DefaultRouter

from vitrina.api.views import (
    CatalogViewSet, CategoryViewSet,
    DatasetDistributionViewSet, DistributionTabularDataViewSet,
    DatasetModelDownloadViewSet, DatasetStructureViewSet, DatasetViewSet,
    InternalDatasetDistributionViewSet, InternalDatasetStructureViewSet, InternalDatasetViewSet,
    LicenceViewSet,
    PartnerApiView,
    UploadToStorageViewSet,
    edp_dcat_ap_rdf,
)

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

    # distribution api urls
    path('partner/api/1/distributions/',
         UploadToStorageViewSet.as_view({
             'get': 'list',
             'post': 'create',
         }), name="api-all-distributions-upload-to-storage"),
    path('partner/api/1/distribution/id/<int:distributionId>/tabular-data/',
         DistributionTabularDataViewSet.as_view({
             'get': 'retrieve',
         }), name="api-distribution-tabular-data"),

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

    path('public/api/1/', TemplateView.as_view(template_name="vitrina/api/public_api.html"), name="public-api"),
    path('edp/dcat-ap.rdf', edp_dcat_ap_rdf, name="edp-dcat-ap-rdf"),
    path('register/account-confirm-email/?P<key>\w+', confirm_email, name='account_confirm_email'),
    path('register/email-verification-sent/', email_verification_sent,
         name='account_email_verification_sent'),
]
