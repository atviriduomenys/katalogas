from django.views import View
from django.views.generic import TemplateView
from django.urls import reverse
from django.shortcuts import render, redirect
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2LoginView,
    OAuth2CallbackView
)
from allauth.socialaccount.helpers import (
    complete_social_login
)
from vitrina.viisp.models import ViispKey, ViispTokenKey
from vitrina.viisp.adapter import VIISPOAuth2Adapter
from vitrina.viisp.provider import VIISPProvider
from vitrina.viisp.xml_utils import get_response_with_ticket_id, \
get_response_with_user_data
from vitrina.helpers import get_current_domain
from base64 import b64decode
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from vitrina.users.models import User
from allauth.account.utils import perform_login
from cryptography.fernet import Fernet
from django.http import HttpResponse

class VIISPLoginView(TemplateView):
    template_name = 'allauth/socialaccount/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        token = None
        encoded_key = ViispKey.objects.first().key_content
        key = b64decode(encoded_key).decode('ascii')
        domain = get_current_domain(request)
        if self.request.user.is_authenticated:
            viisp_token_key = ViispTokenKey.objects.first().key_content.encode()
            fernet = Fernet(viisp_token_key)
            token = fernet.encrypt(self.request.user.email.encode()).decode()
        ticket_id, error_data = get_response_with_ticket_id(key, domain, token)
        if not ticket_id:
            return render(request, 'allauth/socialaccount/api_error.html', error_data)
        url = VIISPOAuth2Adapter.authorize_url
        return redirect(url + "?" + "ticket={}".format(ticket_id))

@method_decorator(csrf_exempt, name='dispatch')
class VIISPCompleteLoginView(View):
    def get(self, request, token=None):
        return redirect('home')

    def post(self, request, token=None):
        encoded_key = ViispKey.objects.first().key_content
        key = b64decode(encoded_key).decode('ascii')
        provider = providers.registry.by_id(VIISPProvider.id, request)
        ticket_id = self.request.POST.get('ticket')
        user_data = get_response_with_user_data(ticket_id, key)
        login = provider.sociallogin_from_response(request, user_data)
        if token:
            viisp_token_key = ViispTokenKey.objects.first().key_content.encode()
            fernet = Fernet(viisp_token_key)
            email = fernet.decrypt(token).decode()
            if email != user_data.get('email'):
                return redirect('change-email')
            else:
                user_data['email'] = email

        if not user_data.get('email'):
            return redirect('change-email')

        user = User.objects.filter(email=user_data.get('email')).first()
        if user and token:
            return perform_login(
                request,
                user,
                email_verification=False,
                redirect_url='complete-login',
                signal_kwargs={"sociallogin": login},
            )
        elif user:
            return redirect('login-first')
        return complete_social_login(request, login)

class ChangeEmailView(TemplateView):
    template_name = 'vitrina/viisp/change_email.html'

class LoginFirstView(TemplateView):
    template_name = 'vitrina/viisp/login_first.html'


oauth2_login = OAuth2LoginView.adapter_view(VIISPOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(VIISPOAuth2Adapter)
