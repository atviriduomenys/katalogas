from django.urls import path

from vitrina.orgs.views import OrganizationSearchResultsView

urlpatterns = [
    # @RequestMapping("/organizations")
    # @GetMapping("/partner/register")
    path('organizations/search/', OrganizationSearchResultsView.as_view(), name='organization-search-results')
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
