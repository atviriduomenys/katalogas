from django.urls import path

from vitrina.resources.views import ResourceCreateView, ResourceUpdateView, ResourceDeleteView

urlpatterns = [
    path('resource/<int:pk>/add', ResourceCreateView.as_view(), name='resource-add'),
    path('resource/<int:pk>/update', ResourceUpdateView.as_view(), name='resource-update'),
    path('resource/<int:pk>/remove', ResourceDeleteView.as_view(), name='resource-remove'),
    # @GetMapping("/resources")
]
