from vitrina.viisp.provider import VIISPProvider
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter
from vitrina.settings import VIISP_AUTHORIZE_URL


class VIISPOAuth2Adapter(OAuth2Adapter):
    provider_id = VIISPProvider.id
    authorize_url = VIISP_AUTHORIZE_URL
    