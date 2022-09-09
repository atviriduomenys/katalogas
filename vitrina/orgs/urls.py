from django.urls import path

from vitrina.orgs.views import OrganizationListView, OrganizationMembersView

urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    #TODO: When organization kind is working implement into link
    path('orgs/<slug:org_slug>/members/', OrganizationMembersView.as_view(), name='org-members-list')
    # @GetMapping("/partner/register")
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
