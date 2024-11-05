from django.urls import path
from vitrina.viisp.provider import VIISPProvider
from vitrina.viisp.views import VIISPLoginView, VIISPCompleteLoginView, ChangeEmailView, LoginFirstView, \
    VIISPAccountMergeView, ConfirmEmailView, AccoutnInactiveView
from vitrina.orgs.views import PartnerRegisterView
from allauth.socialaccount.views import SignupView, ConnectionsView
from django.contrib.auth.decorators import login_required
from django.urls import reverse



from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

class SignupViewViisp(SignupView):

    #@login_required
    def get_authenticated_redirect_url(self):
        return reverse('socialaccount_connections')

urlpatterns = [
    path('viisp/login', VIISPLoginView.as_view(), name='viisp_login'),
    path('viisp/complete-login', VIISPCompleteLoginView.as_view(), name='viisp-complete-login'),
    path('viisp/complete-login/<token>', VIISPCompleteLoginView.as_view(), name='viisp-complete-login-token'),
    path('viisp/account-merge/<token>', VIISPAccountMergeView.as_view(), name='viisp-account-merge'),
    path('viisp/confirm-email/', ConfirmEmailView.as_view(), name='confirm-email'),
    path('viisp/signup', SignupViewViisp.as_view(), name='socialaccount_signup'),
    path('viisp/connections', ConnectionsView.as_view(), name='socialaccount_connections'),
    path('viisp/change-email-view/', ChangeEmailView.as_view(), name='change-email'),
    path('viisp/login-first/', LoginFirstView.as_view(), name='login-first'),
    path('viisp/partner-register/', PartnerRegisterView.as_view(), name='partner-register'),
    path('viisp/account-inactive/', AccoutnInactiveView.as_view(), name='account_inactive'),
]

