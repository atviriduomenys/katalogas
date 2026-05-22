from django.urls import path

from vitrina.dcat.views.dataset_views import DcatDatasetCreateView, DcatDatasetUpdateView, DcatDatasetRelationshipUpdateView
from vitrina.dcat.views.distribution_views import DcatDistributionCreateView, DcatDistributionUpdateView

urlpatterns = [
    path(
        "organization/<int:organization_id>/dcat/dataset/subclass/<uuid:subclass_uuid>/",
        DcatDatasetCreateView.as_view(),
        name="dcat-dataset-create",
    ),
    path(
        "organization/<int:organization_id>/dcat/dataset/parent/<int:parent_id>/subclass/<uuid:subclass_uuid>/",
        DcatDatasetCreateView.as_view(),
        name="dcat-dataset-create-with-parent",
    ),
    path(
        "organization/<int:organization_id>/dcat/dataset/<int:dataset_id>/update/",
        DcatDatasetUpdateView.as_view(),
        name="dcat-dataset-update",
    ),
    path(
        "organization/<int:organization_id>/dcat/dataset/<int:dataset_id>/relationships/update/",
        DcatDatasetRelationshipUpdateView.as_view(),
        name="dcat-dataset-relationships-update",
    ),
    path(
        "organization/<int:organization_id>/dcat/dataset/<int:dataset_id>/distribution/",
        DcatDistributionCreateView.as_view(),
        name="dcat-distribution-create",
    ),
    path(
        "organization/<int:organization_id>/dcat/dataset/<int:dataset_id>/distribution/<int:distribution_id>/update/",
        DcatDistributionUpdateView.as_view(),
        name="dcat-distribution-update",
    ),
    path(
        "organization/<int:organization_id>/dcat/dataset/<int:dataset_id>/distribution/<int:distribution_id>/update/version/<int:version_id>/",
        DcatDistributionUpdateView.as_view(),
        name="dcat-distribution-update-versioned",
    ),
]
