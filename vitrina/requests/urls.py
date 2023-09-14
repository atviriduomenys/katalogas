from django.urls import path

from vitrina.requests.views import RequestDatasetView, RequestOrganizationView, RequestDeleteDatasetView
from vitrina.requests.views import RequestListView, RequestCreateView, RequestUpdateView, RequestHistoryView, \
    RequestPublicationStatsView, RequestYearStatsView, RequestQuarterStatsView, RequestOrgEditView
from vitrina.requests.views import RequestDetailView
from vitrina.requests.views import RequestPlanView
from vitrina.requests.views import RequestCreatePlanView
from vitrina.requests.views import RequestDeletePlanView
from vitrina.requests.views import RequestPlansHistoryView
from vitrina.requests.views import RequestDeletePlanDetailView

urlpatterns = [
    # @GetMapping("/requests/submitted")
    path('requests/submitted/', RequestListView.as_view(), name='request-list'),
    # @GetMapping("/requests/{slug}")
    path('requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),
    path('requests/stats/publication/', RequestPublicationStatsView.as_view(), name='request-stats-published'),
    path('requests/stats/publication/year/<int:year>/', RequestYearStatsView.as_view(), name='request-stats-publication-year'),
    path('requests/stats/publication/quarter/<str:quarter>/', RequestQuarterStatsView.as_view(), name='request-stats-publication-quarter'),
    # @GetMapping("/requests/info")
    # @GetMapping("/requests/request")
    path('requests/add/', RequestCreateView.as_view(), name='request-create'),
    path('requests/<int:pk>/change/', RequestUpdateView.as_view(), name='request-update'),
    path('requests/<int:pk>/history/', RequestHistoryView.as_view(), name='request-history'),
    path('requests/<int:pk>/plans/', RequestPlanView.as_view(), name='request-plans'),
    path('requests/<int:pk>/plans/add/', RequestCreatePlanView.as_view(), name='request-plans-create'),
    path('requests/plans/<int:pk>/delete/', RequestDeletePlanView.as_view(), name='request-plans-delete'),
    path('requests/<int:pk>/plans/history/', RequestPlansHistoryView.as_view(), name='request-plans-history'),
    path('requests/plans/<int:pk>/detail/delete/', RequestDeletePlanDetailView.as_view(),
         name='request-plans-delete-detail'),
    path('requests/<int:pk>/datasets/', RequestDatasetView.as_view(), name='request-datasets'),
    path('requests/<int:pk>/orgs/', RequestOrganizationView.as_view(), name='request-organizations'),
    path('requests/<int:pk>/orgs/add/<str:mode>', RequestOrgEditView.as_view(), name='request-orgs-edit'),
    path('requests/<int:pk>/datasets/<int:dataset_id>/remove', RequestDeleteDatasetView.as_view(),
         name='request-dataset-remove'),
    # @PostMapping("/request")
    # @PostMapping("/requests/new")
    # @PostMapping("/request/{id}/comment")
    # @PostMapping("/request/{id}/reply")
    # @GetMapping("/requests/suggestions")
    # @GetMapping("/requests/suggest")
    # @PostMapping("/suggest")
]
