from django.urls import path

from vitrina.requests.views import RequestListView, RequestCreateView, RequestUpdateView, RequestHistoryView
from vitrina.requests.views import RequestDetailView

urlpatterns = [
    # @GetMapping("/requests/submitted")
    path('requests/submitted/', RequestListView.as_view(), name='request-list'),
    # @GetMapping("/requests/{slug}")
    path('requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),
    # @GetMapping("/requests/info")
    # @GetMapping("/requests/request")
    path('requests/add/', RequestCreateView.as_view(), name='request-create'),
    path('requests/<int:pk>/update/', RequestUpdateView.as_view(), name='request-update'),
    path('requests/<int:pk>/history/', RequestHistoryView.as_view(), name='request-history'),
    # @PostMapping("/request")
    # @PostMapping("/requests/new")
    # @PostMapping("/request/{id}/comment")
    # @PostMapping("/request/{id}/reply")
    # @GetMapping("/requests/suggestions")
    # @GetMapping("/requests/suggest")
    # @PostMapping("/suggest")
]
