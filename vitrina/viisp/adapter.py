from vitrina.viisp.provider import VIISPProvider
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from vitrina.settings import VIISP_AUTHORIZE_URL
from vitrina.users.models import User
from allauth.account.utils import (
    complete_signup,
    perform_login,
    user_display,
    user_username,
)

class VIISPOAuth2Adapter(OAuth2Adapter):
    provider_id = VIISPProvider.id
    authorize_url = VIISP_AUTHORIZE_URL

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_ajax(self, request):
        return any(
            [
                request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest",
                request.content_type == "application/json",
                request.META.get("HTTP_ACCEPT") == "application/json",
            ]
        )
    def pre_social_login(self, request, sociallogin): 
        user = sociallogin.user
        if user.id:  
            return          
        try:
            user = User.objects.get(email=user.email)  # if user exists, connect the account to the existing account and login
            sociallogin.state['process'] = 'connect'                
            perform_login(request, user, 'none')
        except User.DoesNotExist:
            pass