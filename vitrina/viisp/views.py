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
from vitrina.messages.helpers import prepare_email_by_identifier_for_sub
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
from allauth.socialaccount.models import SocialAccount
from itsdangerous.url_safe import URLSafeSerializer
from vitrina.helpers import send_email_with_logging
import bcrypt



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
    base_template_content = """
        Pabaikite registraciją su viisp, patvirtinant elektroninį paštą:\n'
    '{0}   
    """
    email_identifier = "auth-viisp-merge"
    def get(self, request, token=None):
        return redirect('home')

    def post(self, request, token=None):
        encoded_key = ViispKey.objects.first().key_content
        key = b64decode(encoded_key).decode('ascii')
        provider = providers.registry.by_id(VIISPProvider.id, request)
        ticket_id = self.request.POST.get('ticket')
        user_data = get_response_with_user_data(ticket_id, key)
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
        
        if not user_data.get('personal_code'):
            error_data = {}
            return render(request, 'allauth/socialaccount/api_error.html', error_data)

        user = User.objects.filter(email=user_data.get('email')).first()
        login = provider.sociallogin_from_response(request, user_data)
        if user:
            user_social_account = SocialAccount.objects.filter(user__email=user).first()
            if token:
                return perform_login(
                    request,
                    user,
                    email_verification=False,
                    redirect_url='complete-login',
                    signal_kwargs={"sociallogin": login},
                )
            elif user_social_account:
                personal_code_bytes = user_data.get('personal_code').encode('utf-8')
                if bcrypt.checkpw(personal_code_bytes, user_social_account.extra_data.get('personal_code').encode('utf-8')):
                    if not user_social_account.extra_data.get('password_not_set'):
                        return perform_login(
                            request,
                            user,
                            email_verification=False,
                            redirect_url='complete-login',
                            signal_kwargs={"sociallogin": login},
                        )
                    else:
                        return perform_login(
                            request,
                            user,
                            email_verification=False,
                            redirect_url='complete-login',
                            signal_kwargs={"sociallogin": login},
                        )
            else:
                viisp_token_key = ViispTokenKey.objects.first().key_content
                s = URLSafeSerializer(viisp_token_key)
                token = s.dumps([user_data.get(key) for key in user_data])
                sub_email_list = [user_data.get('email')]
                url = "%s%s" % (
                    get_current_domain(self.request),
                    reverse('viisp-account-merge', kwargs={'token': token})
                )
                email_data = prepare_email_by_identifier_for_sub(
                    self.email_identifier,  self.base_template_content,
                    'Elektroninio pašto patvirtinimas',
                    [url]
                )
                send_email_with_logging(email_data, sub_email_list)
                return redirect('confirm-email')
        return complete_social_login(request, login)


class ChangeEmailView(TemplateView):
    template_name = 'vitrina/viisp/change_email.html'

class LoginFirstView(TemplateView):
    template_name = 'vitrina/viisp/login_first.html'

class ConfirmEmailView(TemplateView):
    template_name = 'vitrina/viisp/confirm_email.html'


@method_decorator(csrf_exempt, name='dispatch')
class VIISPAccountMergeView(View):
    def get(self, request, token=None):
        if token:
            if token == 'password-set':
                return redirect('password-set')
            viisp_token_key = ViispTokenKey.objects.first().key_content
            s = URLSafeSerializer(viisp_token_key)
            merge_data = None
            merge_data_dict = {}
            try:
                merge_data = s.loads(token)
                merge_data_dict = {
                    'personal_code': merge_data[0],
                    'first_name': merge_data[1],
                    'last_name': merge_data[2],
                    'email': merge_data[3],
                    'phone': merge_data[4],
                    'ticket_id': merge_data[5]
                }
            except:
                return redirect('home')
            provider = providers.registry.by_id(VIISPProvider.id, request)
            login = provider.sociallogin_from_response(request, merge_data_dict)
            user = User.objects.filter(email=merge_data_dict.get('email')).first()
            return perform_login(
                request,
                user,
                email_verification=False,
                redirect_url='password-set',
                signal_kwargs={"sociallogin": login},
            )
        return redirect('home')

oauth2_login = OAuth2LoginView.adapter_view(VIISPOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(VIISPOAuth2Adapter)
