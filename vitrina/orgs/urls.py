from django.urls import path

from vitrina.datasets.views import DatasetListView
from vitrina.orgs.views import OrganizationListView, RepresentativeCreateView, RepresentativeUpdateView, \
    RepresentativeDeleteView
from vitrina.orgs.views import OrganizationDetailView, OrganizationMembersView, RepresentativeRegisterView

urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('orgs/<int:pk>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('orgs/<int:pk>/members/', OrganizationMembersView.as_view(), name='organization-members'),
    path('orgs/<int:pk>/datasets/', DatasetListView.as_view(), name='organization-datasets'),
    path('orgs/<int:organization_id>/members/add/', RepresentativeCreateView.as_view(),
         name='representative-create'),
    path('orgs/<int:organization_id>/members/<int:pk>/update/', RepresentativeUpdateView.as_view(),
         name='representative-update'),
    path('orgs/<int:organization_id>/members/<int:pk>/remove/', RepresentativeDeleteView.as_view(),
         name='representative-remove'),
    path('register/<token>/', RepresentativeRegisterView.as_view(), name='representative-register'),
    # @GetMapping("/partner/register")
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
