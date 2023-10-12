from django.urls import path

from vitrina.datasets.views import DatasetListView
from vitrina.orgs.views import OrganizationListView, RepresentativeCreateView, RepresentativeUpdateView, \
    RepresentativeDeleteView, OrganizationManagementsView, OrganizationUpdateView
from vitrina.orgs.views import OrganizationDetailView, OrganizationMembersView, \
     RepresentativeRegisterView, PartnerRegisterInfoView, \
     PartnerRegisterView, OrganizationPlanView, OrganizationPlanCreateView
from vitrina.orgs.views import OrganizationPlansHistoryView
from vitrina.orgs.views import OrganizationMergeView
from vitrina.orgs.views import ConfirmOrganizationMergeView
from vitrina.orgs.views import RepresentativeApiKeyView

urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('organizations/stats/jurisdiction/', OrganizationManagementsView.as_view(), name='organization-stats-jurisdiction'),
    path('orgs/<int:pk>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('orgs/<int:pk>/update/', OrganizationUpdateView.as_view(), name='organization-change'),
    path('orgs/<int:pk>/members/', OrganizationMembersView.as_view(), name='organization-members'),
    path('orgs/<int:pk>/datasets/', DatasetListView.as_view(), name='organization-datasets'),
    path('orgs/<int:organization_id>/members/add/', RepresentativeCreateView.as_view(),
         name='representative-create'),
    path('orgs/<int:organization_id>/members/<int:pk>/change/', RepresentativeUpdateView.as_view(),
         name='representative-update'),
    path('orgs/<int:organization_id>/members/<int:pk>/delete/', RepresentativeDeleteView.as_view(),
         name='representative-delete'),
    path('register/<token>/', RepresentativeRegisterView.as_view(), name='representative-register'),
    path('partner/register-info/', PartnerRegisterInfoView.as_view(), name='partner-register-info'),
    path('partner/register/', PartnerRegisterView.as_view(), name='partner-register'),
    path('orgs/<int:pk>/plans/', OrganizationPlanView.as_view(), name='organization-plans'),
    path('orgs/<int:pk>/plans/add/', OrganizationPlanCreateView.as_view(), name='organization-plans-create'),
    path('orgs/<int:pk>/plans/history/', OrganizationPlansHistoryView.as_view(), name='organization-plans-history'),
    path('orgs/<int:pk>/merge/', OrganizationMergeView.as_view(), name='merge-organizations'),
    path('orgs/<int:organization_id>/<int:merge_organization_id>/merge/confirm/',
         ConfirmOrganizationMergeView.as_view(), name='confirm-organization-merge'),
    path('orgs/<int:pk>/members/<int:rep_id>/api/<key>', RepresentativeApiKeyView.as_view(),
         name='representative-api-key'),
    # @GetMapping("/partner/register")
    # @PostMapping("/partner/register")
    # @GetMapping("/group")
    # @GetMapping("/report")
    # @PostMapping("/report")
    # @GetMapping("/dictionary")
]
