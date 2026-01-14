from django.urls import path

from vitrina.resources.views import (
    ResourceCreateView,
    ResourceUpdateView,
    ResourceDeleteView,
    DynamicResourceDetailView,
)
from vitrina.resources.views import ResourceDetailView
from vitrina.resources.views import ResourceModelCreateView

urlpatterns = [
    path("resource/<int:pk>/add", ResourceCreateView.as_view(), name="resource-add"),
    path("resource/<int:pk>/versions/<int:version_id>/change", ResourceUpdateView.as_view(), name="resource-change"),
    path("resource/<int:pk>/change", ResourceUpdateView.as_view(), name="resource-change-no-version"),
    path("resource/<int:pk>/versions/<int:version_id>/delete", ResourceDeleteView.as_view(), name="resource-delete"),
    path("resource/<int:pk>/delete", ResourceDeleteView.as_view(), name="resource-delete-no-version"),
    path(
        "datasets/<int:pk>/versions/<int:version_id>/resource/<int:resource_id>",
        ResourceDetailView.as_view(),
        name="resource-detail",
    ),
    path(
        "datasets/<int:pk>/resource/<int:resource_id>",
        ResourceDetailView.as_view(),
        name="resource-detail-no-version",
    ),
    path(
        "datasets/<int:pk>/versions/<int:version_id>/resource/<int:resource_id>/<str:distribution_name>/<str:format>",
        DynamicResourceDetailView.as_view(),
        name="dynamic-resource-detail",
    ),
    path(
        "datasets/<int:pk>/resource/<int:resource_id>/<str:distribution_name>/<str:format>",
        DynamicResourceDetailView.as_view(),
        name="dynamic-resource-detail-no-version",
    ),
    path(
        "datasets/<int:pk>/versions/<int:version_id>/resource/<int:resource_id>/models/add/",
        ResourceModelCreateView.as_view(),
        name="resource-model-create",
    ),
]
