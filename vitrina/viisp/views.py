from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2LoginView,
    OAuth2CallbackView
)
from vitrina.viisp.adapter import VIISPOAuth2Adapter
from vitrina.viisp.xml_utils import get_response_with_ticket_id, \
get_response_with_user_data

class VIISPLoginView(TemplateView):
    template_name = 'allauth/socialaccount/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        ticket_id = get_response_with_ticket_id()
        url = VIISPOAuth2Adapter.authorize_url
        return redirect(url + "?" + "ticket={}".format(ticket_id))

class VIISPCompleteLoginView(TemplateView):
    template_name = 'allauth/socialaccount/complete_login.html'
    def post(self, request):
        ticket_id = self.request.POST.get('ticket')
        user_data = get_response_with_user_data(ticket_id)
        return render(request, self.template_name, user_data)
