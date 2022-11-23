import requests

from allauth.socialaccount.providers.oauth2.views import (
    OAuth2LoginView,
    OAuth2CallbackView,
    OAuth2Adapter,
)
from vitrina.viisp.providers import VIISPProvider


class VIISPOAuth2Adapter(OAuth2Adapter):
    provider_id = VIISPProvider.id
    access_token_url = "https://test.epaslaugos.lt:443/portal/authenticationServices/auth"
    authorize_url = "https://test.epaslaugos.lt/portal/external/services/authentication/v2"

    def complete_login(self, request, app, token, **kwargs):
        response = requests.get(self.authorize_url, params={"access_token": token})
        extra_data = response.json()
        return self.get_provider().sociallogin_from_response(request, extra_data)


oauth2_login = OAuth2LoginView.adapter_view(VIISPOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(VIISPOAuth2Adapter)
