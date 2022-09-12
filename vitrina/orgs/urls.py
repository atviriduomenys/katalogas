from django.urls import path

from vitrina.datasets.views import DatasetListView
from vitrina.orgs.views import OrganizationListView
from vitrina.orgs.views import OrganizationDetailView, OrganizationMembersView

urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('orgs/<str:kind>/<slug:slug>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('orgs/<str:kind>/<str:slug>/members/', OrganizationMembersView.as_view(),
         name='organization-members'),
    path('orgs/<str:kind>/<str:slug>/datasets/', DatasetListView.as_view(), name='organization-datasets'),
    # @GetMapping("/partner/register")
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
