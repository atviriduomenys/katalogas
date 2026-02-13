from django.urls import path

from vitrina.uapi.views.agreement_file_views import AgreementFileDownloadUAPIView
from vitrina.uapi.views.agreement_views import AgreementViewSet

from vitrina.uapi.views.template_views import (
    AgentDeleteView,
    AgentUpdateView,
    AgentCreateView,
    AgentDetailView,
    AgentListView,
    RequestDetailView,
)
from vitrina.uapi.views.views import (
    DatasetViewSet,
    DistributionViewSet,
    AgentSyncDoneViewSet,
    VersionViewSet,
    AgentViewSet,
    ConnectionViewSet,
)


STATIC_UAPI_BASE_PATH = "uapi/datasets/gov/vssa/ror/dcat/"


urlpatterns = [
    path(
        "organizations/<int:organization_id>/agents/<uuid:agent_id>/history/<uuid:pk>/",
        RequestDetailView.as_view(),
        name="request-history",
    ),
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
        name="agent-update",
    ),
    path(
        "organizations/<int:organization_id>/agents/<uuid:pk>/delete/",
        AgentDeleteView.as_view(),
        name="agent-delete",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Connection/check",
        ConnectionViewSet.as_view({"post": "check"}),
        name="connection-check",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Dataset/",
        DatasetViewSet.as_view({"post": "create", "get": "list"}),
        name="uapi-dataset",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Dataset/<str:pk>/dsa/",
        DatasetViewSet.as_view(
            {
                "post": "upload_dataset_structure",
                "get": "get_dataset_structure",
                "put": "update_dataset_structure",
            }
        ),
        name="uapi-dataset-structure",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Distribution/",
        DistributionViewSet.as_view({"post": "create", "get": "list"}),
        name="uapi-distribution",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Agreement/",
        AgreementViewSet.as_view({"get": "list"}),
        name="uapi-agreement",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Agreement/<uuid:agreement_id>/sync-done/",
        AgentSyncDoneViewSet.as_view({"put": "update"}),
        name="uapi-agent-sync-done",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Version/",
        VersionViewSet.as_view({"get": "list"}),
        name="uapi-version",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}Agent/",
        AgentViewSet.as_view({"get": "list"}),
        name="uapi-agent",
    ),
    path(
        f"{STATIC_UAPI_BASE_PATH}AgreementFile/<uuid:agreement_file_uuid>/file/",
        AgreementFileDownloadUAPIView.as_view(),
        name="uapi-agreement-file-download",
    ),
]
