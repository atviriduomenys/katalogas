from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2LoginView,
    OAuth2CallbackView
)
from allauth.socialaccount.helpers import (
    complete_social_login
)
from vitrina.viisp.models import ViispKey
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

class VIISPLoginView(TemplateView):
    template_name = 'allauth/socialaccount/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        encoded_key = ViispKey.objects.first().key_content
        key = b64decode(encoded_key).decode('ascii')
        domain = get_current_domain(request)
        ticket_id = get_response_with_ticket_id(key, domain)
        url = VIISPOAuth2Adapter.authorize_url
        return redirect(url + "?" + "ticket={}".format(ticket_id))

@method_decorator(csrf_exempt, name='dispatch')
class VIISPCompleteLoginView(View):
    def post(self, request):
        encoded_key = ViispKey.objects.first().key_content
        key = b64decode(encoded_key).decode('ascii')
        provider = providers.registry.by_id(VIISPProvider.id, request)
        ticket_id = self.request.POST.get('ticket')
        user_data = get_response_with_user_data(ticket_id, key)
        login = provider.sociallogin_from_response(request, user_data)
        user = User.objects.filter(email=user_data.get('email')).first()
        if user:
            return perform_login(
                request,
                user,
                email_verification=False,
                redirect_url=login.get_redirect_url(request),
                signal_kwargs={"sociallogin": login},
            )
        return complete_social_login(request, login)

oauth2_login = OAuth2LoginView.adapter_view(VIISPOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(VIISPOAuth2Adapter)
