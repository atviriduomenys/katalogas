from django.urls import path

from vitrina.datasets.views import DatasetListView
from vitrina.orgs.views import OrganizationListView, RepresentativeCreateView, RepresentativeUpdateView, \
    RepresentativeDeleteView, OrganizationManagementsView, OrganizationUpdateView, OrganizationApiKeysView, \
    OrganizationApiKeysCreateView, OrganizationApiKeysUpdateView, OrganizationApiKeysDeleteView, \
    OrganizationApiKeysDetailView, OrganizationApiKeysScopeCreateView, OrganizationApiKeysScopeChangeView, \
    OrganizationApiKeysScopeDeleteView, OrganizationApiKeysScopeToggleView, OrganizationApiKeysRegenerateView, \
    OrganizationApiKeysScopeObjectChangeView, OrganizationApiKeysScopeObjectDeleteView, \
    OrganizationApiKeysScopeObjectToggleView, OrganizationApiKeysToggleView
from vitrina.orgs.views import OrganizationDetailView, OrganizationMembersView, \
     RepresentativeRegisterView, PartnerRegisterInfoView, \
     PartnerRegisterView, OrganizationPlanView, OrganizationPlanCreateView, \
     RepresentativeRequestApproveView, RepresentativeRequestDenyView, PartnerRegisterCompleteView, \
          RepresentativeRequestDownloadView, RepresentativeRequestSuspendView
from vitrina.orgs.views import OrganizationPlansHistoryView
from vitrina.orgs.views import OrganizationMergeView
from vitrina.orgs.views import ConfirmOrganizationMergeView
from vitrina.orgs.views import RepresentativeApiKeyView
from vitrina.orgs.views import RepresentativeExistsView
from vitrina.orgs.views import OrganizationCreateSearchView, OrganizationCreateView, OrganizationCreateSearchUpdateView


urlpatterns = [
    # @RequestMapping("/organizations")
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('organizations/stats/jurisdiction/', OrganizationManagementsView.as_view(),
         name='organization-stats-jurisdiction'),
    path('orgs/<int:pk>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('orgs/<int:pk>/update/', OrganizationUpdateView.as_view(), name='organization-change'),
    path('orgs/create/search-update', OrganizationCreateSearchUpdateView.as_view(), name='organization-create-search-update'),
    path('orgs/create/search', OrganizationCreateSearchView.as_view(), name='organization-create-search'),
    path('orgs/create/', OrganizationCreateView.as_view(), name='organization-create'),
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
    path('partner/register-complete/', PartnerRegisterCompleteView.as_view(), name='partner-register-complete'),
    path('partner/approve/<int:pk>/', RepresentativeRequestApproveView.as_view(), name='partner-register-approve'),
    path('partner/deny/<int:pk>/', RepresentativeRequestDenyView.as_view(), name='partner-register-deny'),
    path('partner/suspend/<int:pk>/', RepresentativeRequestSuspendView.as_view(), name='partner-register-suspend'),
    path('partner/download/<int:pk>/', RepresentativeRequestDownloadView.as_view(), name='partner-register-download'),
    path('partner/exists/', RepresentativeExistsView.as_view(), name='representative-exists'),
    path('orgs/<int:pk>/plans/', OrganizationPlanView.as_view(), name='organization-plans'),
    path('orgs/<int:pk>/plans/add/', OrganizationPlanCreateView.as_view(), name='organization-plans-create'),
    path('orgs/<int:pk>/apikeys/', OrganizationApiKeysView.as_view(), name='organization-apikeys'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/', OrganizationApiKeysDetailView.as_view(),
         name='organization-apikeys-detail'),
    path('orgs/<int:pk>/apikeys/add/', OrganizationApiKeysCreateView.as_view(), name='organization-apikeys-create'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/change/', OrganizationApiKeysUpdateView.as_view(),
         name='organization-apikeys-update'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/regenerate/', OrganizationApiKeysRegenerateView.as_view(),
         name='organization-apikeys-regenerate'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/remove/', OrganizationApiKeysDeleteView.as_view(),
         name='organization-apikeys-delete'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/scope/add/', OrganizationApiKeysScopeCreateView.as_view(),
         name='organization-apikeys-scope-create'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/<str:scope>/change/', OrganizationApiKeysScopeChangeView.as_view(),
         name='organization-apikeys-scope-change'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/<int:content_type_id>/<int:obj_id>/change/',
         OrganizationApiKeysScopeObjectChangeView.as_view(), name='organization-apikeys-scope-object-change'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/<str:scope>/delete/', OrganizationApiKeysScopeDeleteView.as_view(),
         name='organization-apikeys-scope-delete'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/<int:content_type_id>/<int:obj_id>/delete/',
         OrganizationApiKeysScopeObjectDeleteView.as_view(), name='organization-apikeys-scope-object-delete'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/<str:scope>/toggle/', OrganizationApiKeysScopeToggleView.as_view(),
         name='organization-apikeys-scope-toggle'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/toggle/', OrganizationApiKeysToggleView.as_view(),
         name='organization-apikeys-toggle'),
    path('orgs/<int:pk>/apikeys/<int:apikey_id>/<int:content_type_id>/<int:obj_id>/toggle/',
         OrganizationApiKeysScopeObjectToggleView.as_view(), name='organization-apikeys-scope-object-toggle'),
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
