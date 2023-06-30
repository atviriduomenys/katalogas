from django.urls import path
from vitrina.viisp.provider import VIISPProvider
from vitrina.viisp.views import VIISPLoginView, VIISPCompleteLoginView

from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns



urlpatterns = [
    path('viisp/login', VIISPLoginView.as_view(), name='viisp_login'),
    path('viisp/complete-login', VIISPCompleteLoginView.as_view(), name='viisp-complete-login'),
]

