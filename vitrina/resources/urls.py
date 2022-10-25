from django.urls import path

from vitrina.resources.views import ResourceCreateView, ResourceUpdateView, ResourceDeleteView

urlpatterns = [
    path('resource/<int:pk>/add', ResourceCreateView.as_view(), name='resource-add'),
    path('resource/<int:pk>/change', ResourceUpdateView.as_view(), name='resource-change'),
    path('resource/<int:pk>/delete', ResourceDeleteView.as_view(), name='resource-delete'),
    # @GetMapping("/resources")
]
