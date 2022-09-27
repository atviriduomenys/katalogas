from django.urls import path

from vitrina.datasets.views import DatasetListView
from vitrina.orgs.views import OrganizationListView
from vitrina.orgs.views import OrganizationDetailView, OrganizationMembersView

urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('orgs/<int:pk>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('orgs/<int:pk>/members/', OrganizationMembersView.as_view(), name='organization-members'),
    path('orgs/<int:pk>/datasets/', DatasetListView.as_view(), name='organization-datasets'),
    # @GetMapping("/partner/register")
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
