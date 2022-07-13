from django.urls import path

from vitrina.orgs.views import OrganizationListView
from vitrina.orgs.views import OrganizationDetailView

urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('organizations/<kind>/<slug:slug>/', OrganizationDetailView.as_view(), name='organization-detail'),
    # @GetMapping("/partner/register")
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
