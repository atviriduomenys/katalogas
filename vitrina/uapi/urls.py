from django.urls import path
from vitrina.uapi.views.template_views import AgentDeleteView, AgentUpdateView, AgentCreateView, AgentDetailView, AgentListView, RequestDetailView
from vitrina.uapi.views.views import DatasetViewSet, DistributionViewSet


STATIC_UAPI_BASE_PATH = "uapi/datasets/org/vssa/isris/dcat/"


urlpatterns = [
    path(
        "organizations/<int:organization_id>/agents/",
        AgentListView.as_view(),
        name="agent-list",
    ),
    path(
        "organizations/<int:organization_id>/agents/<uuid:pk>/",
        AgentDetailView.as_view(),
        name="agent-detail",
    ),
    path(
        "organizations/<int:organization_id>/agents/add/",
        AgentCreateView.as_view(),
        name="agent-create",
    ),
    path(
        "organizations/<int:organization_id>/agents/<uuid:pk>/update/",
        AgentUpdateView.as_view(),
        name="agent-update"
    ),
    path(
        "organizations/<int:organization_id>/agents/<uuid:pk>/delete/",
        AgentDeleteView.as_view(),
        name="agent-delete"
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Dataset/",
        DatasetViewSet.as_view({"post": "create", "get": "list"}),
        name="uapi-dataset",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Dataset/<str:dataset_id>/dsa/",
        DatasetViewSet.as_view({
            "post": "upload_dataset_structure",
            "put": "update_dataset_structure",
        }),
        name="uapi-dataset-structure",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Distribution/",
        DistributionViewSet.as_view({"post": "create", "get": "list"}),
        name="uapi-distribution",
    ),
    path("request-history/<uuid:pk>/", RequestDetailView.as_view(), name="request-history"),
]
