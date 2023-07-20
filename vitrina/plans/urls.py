from django.urls import path

from vitrina.plans.views import PlanDetailView
from vitrina.plans.views import PlanUpdateView
from vitrina.plans.views import PlanDeleteView
from vitrina.plans.views import PlanHistoryView

urlpatterns = [
    path('orgs/<int:pk>/plans/<int:plan_id>/', PlanDetailView.as_view(), name='plan-detail'),
    path('orgs/<int:pk>/plans/<int:plan_id>/change/', PlanUpdateView.as_view(), name='plan-change'),
    path('orgs/<int:pk>/plans/<int:plan_id>/delete/', PlanDeleteView.as_view(), name='plan-delete'),
    path('orgs/<int:pk>/plans/<int:plan_id>/history/', PlanHistoryView.as_view(), name='plan-history'),
]
