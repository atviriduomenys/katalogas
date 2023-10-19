from django.urls import path

from vitrina.statistics.views import StatRouteListView

urlpatterns = [
    path('stats/', StatRouteListView.as_view(), name='stat-route-list'),
]
