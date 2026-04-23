from django.urls import path

from vitrina.dcat.views import DcatDatasetCreateView, DcatDatasetUpdateView

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
]
