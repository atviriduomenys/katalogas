from django.urls import path
from vitrina.viisp.views import VIISPLoginView, VIISPCompleteLoginView
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('accounts/viisp/login', VIISPLoginView.as_view(), name='viisp-login'),
    path('accounts/viisp/complete-login', csrf_exempt(VIISPCompleteLoginView.as_view()), name='viisp-complete-login'),
]
