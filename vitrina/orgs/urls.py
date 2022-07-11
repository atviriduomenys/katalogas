from django.urls import path

from vitrina.orgs.views import OrganizationListView
from vitrina.orgs.views import OrganizationSearchResultsView

urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('organizations/search/', OrganizationSearchResultsView.as_view(), name='organization-search-results')
    # @GetMapping("/partner/register")
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
