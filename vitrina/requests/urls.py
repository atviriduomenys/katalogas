from django.urls import path

from vitrina.requests.views import RequestListView
from vitrina.requests.views import RequestDetailView

urlpatterns = [
    # @GetMapping("/requests/submitted")
    path('requests/submitted/', RequestListView.as_view(), name='request-list'),
    # @GetMapping("/requests/{slug}")
    path('requests/<pk>/', RequestDetailView.as_view(), name='request-detail'),
    # @GetMapping("/requests/info")
    # @GetMapping("/requests/request")
    # @GetMapping("/requests/new")
    # @GetMapping("/request/modify/{id}")
    # @PostMapping("/request")
    # @PostMapping("/requests/new")
    # @PostMapping("/request/{id}/comment")
    # @PostMapping("/request/{id}/reply")
    # @PostMapping("/request/{id}/like")
    # @GetMapping("/requests/suggestions")
    # @GetMapping("/requests/suggest")
    # @PostMapping("/suggest")
]
