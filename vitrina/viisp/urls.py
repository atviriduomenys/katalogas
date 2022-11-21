from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from vitrina.viisp.providers import VIISPProvider

urlpatterns = default_urlpatterns(VIISPProvider)
