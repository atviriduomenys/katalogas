from django.urls import path

from vitrina.uapi.views import AgentDeleteView, AgentUpdateView, AgentCreateView, AgentDetailView, AgentListView, \
    AgentSync

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
        "organizations/<int:organization_id>/agents/<uuid:pk>/update",
        AgentUpdateView.as_view(),
        name="agent-update"
    ),
    path(
        "organizations/<int:organization_id>/agents/<uuid:pk>/delete",
        AgentDeleteView.as_view(),
        name="agent-delete"
    ),
    path(
        "organizations/agents/sync",
        AgentSync.as_view(),
        name="agent-sync"
    ),
]
