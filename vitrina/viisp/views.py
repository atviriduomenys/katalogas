from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBase, Http404
from django.views import View
from django.views.generic import TemplateView
from django.urls import reverse
from django.shortcuts import render, redirect
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2LoginView,
    OAuth2CallbackView,
)
from allauth.socialaccount.helpers import complete_social_login

from vitrina.orgs.models import Representative
from vitrina.viisp.forms import FakeViispForm
from vitrina.viisp.models import ViispKey, ViispTokenKey
from vitrina.viisp.adapter import VIISPOAuth2Adapter
from vitrina.viisp.provider import VIISPProvider
from vitrina.viisp.xml_utils import get_response_with_ticket_id
from vitrina.viisp.xml_utils import get_response_with_user_data
from vitrina.helpers import get_current_domain, email
from base64 import b64decode
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from vitrina.users.models import User
from allauth.account.utils import perform_login
from cryptography.fernet import Fernet, InvalidToken
from allauth.socialaccount.models import SocialAccount
from itsdangerous.url_safe import URLSafeSerializer
from itsdangerous import BadData
from django.contrib.auth.views import LoginView
import bcrypt


ACCEPTED_PROXY_TYPES = ["generic", "legal"]


def _viisp_api_error(request, error_data=None):
    return render(request, "allauth/socialaccount/api_error.html", error_data or {})


def _set_company_code(target_user, user_data):
    if user_data.get("proxy_type", "").lower() in ACCEPTED_PROXY_TYPES:
        target_user.viisp_company_code = user_data.get("lt_company_code")
    else:
        target_user.viisp_company_code = None


def _mark_viisp_login(target_user, user_data):
    target_user.is_viisp_login = True
    _set_company_code(target_user, user_data)
    target_user.save()


class VIISPLoginView(TemplateView):
    template_name = "allauth/socialaccount/login.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        token = None
        viisp_key = ViispKey.objects.first()
        if not viisp_key:
            return _viisp_api_error(request)
        key = b64decode(viisp_key.key_content).decode("ascii")
        domain = get_current_domain(request, ensure_secure=True)
        if self.request.user.is_authenticated:
            viisp_token_key = ViispTokenKey.objects.first()
            if not viisp_token_key:
                return _viisp_api_error(request)
            fernet = Fernet(viisp_token_key.key_content.encode())
            token = fernet.encrypt(self.request.user.email.encode()).decode()
        ticket_id, error_data = get_response_with_ticket_id(key, domain, token)
        if not ticket_id:
            return _viisp_api_error(request, error_data)
        url = VIISPOAuth2Adapter.authorize_url
        return redirect(url + "?" + "ticket={}".format(ticket_id))


@method_decorator(csrf_exempt, name="dispatch")
class VIISPCompleteLoginView(View):
    def get(self, request, token=None):
        return redirect("home")

    def post(self, request, token=None):
        viisp_key = ViispKey.objects.first()
        if not viisp_key:
            return _viisp_api_error(request)
        key = b64decode(viisp_key.key_content).decode("ascii")
        provider = VIISPProvider(request)
        ticket_id = self.request.POST.get("ticket")
        if not ticket_id:
            return _viisp_api_error(request)
        user_data = get_response_with_user_data(ticket_id, key)
        if not user_data:
            return _viisp_api_error(request)
        if token:
            viisp_token_key = ViispTokenKey.objects.first()
            if not viisp_token_key:
                return _viisp_api_error(request)
            fernet = Fernet(viisp_token_key.key_content.encode())
            try:
                email = fernet.decrypt(token).decode()
            except (InvalidToken, ValueError):
                return _viisp_api_error(request)
            if email.lower() != (user_data.get("email") or "").lower():
                return redirect("change-email")
            else:
                user_data["email"] = email

        if not user_data.get("email"):
            return redirect("change-email")

        if not user_data.get("personal_code"):
            return _viisp_api_error(request)

        user = User.objects.filter(email=user_data.get("email")).first()
        if user:
            user_social_account = SocialAccount.objects.filter(user=user, provider=VIISPProvider.id).first()
            if token:
                _mark_viisp_login(user, user_data)
                login = provider.sociallogin_from_response(request, user_data)
                return perform_login(
                    request,
                    user,
                    email_verification=False,
                    redirect_url=reverse("partner-register"),
                    signal_kwargs={"sociallogin": login},
                )
            elif user_social_account:
                stored_personal_code = user_social_account.extra_data.get("personal_code")
                if not stored_personal_code:
                    return _viisp_api_error(request)
                login = provider.sociallogin_from_response(request, user_data)
                if bcrypt.checkpw(
                    user_data.get("personal_code").encode("utf-8"),
                    stored_personal_code.encode("utf-8"),
                ):
                    _mark_viisp_login(user, user_data)
                    if not user_social_account.extra_data.get("password_not_set"):
                        return perform_login(
                            request,
                            user,
                            email_verification=False,
                            redirect_url="complete-login",
                            signal_kwargs={"sociallogin": login},
                        )
                    else:
                        return perform_login(
                            request,
                            user,
                            email_verification=False,
                            redirect_url=reverse("password-set"),
                            signal_kwargs={"sociallogin": login},
                        )
                else:
                    return _viisp_api_error(request)
            else:
                _mark_viisp_login(user, user_data)
                if not _confirm_viisp_email(
                    user_data.get("email"),
                    user_data,
                    get_current_domain(self.request),
                ):
                    return _viisp_api_error(request)
                return redirect("confirm-email")
        login = provider.sociallogin_from_response(request, user_data)
        response = complete_social_login(request, login)

        # update related representatives
        if login.user:
            if reps := Representative.objects.filter(email=login.user.email, user__isnull=True):
                reps.update(user=login.user)
            login.user.is_viisp_login = True
            _set_company_code(login.user, user_data)
            login.user.save()

        return response


class FakeVIISPCompleteLoginView(LoginView):
    """Fake VIISP login for debug/testing purposes only."""

    template_name = "vitrina/viisp/fake_viisp_form.html"
    form_class = FakeViispForm
    redirect_authenticated_user = True

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        if not settings.DEBUG:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form) -> HttpResponse:
        user: User = form.get_user()
        user.is_viisp_login = True
        if company_code := form.cleaned_data.get("lt_company_code"):
            user.viisp_company_code = company_code
        else:
            user.viisp_company_code = None

        user.save()

        return super().form_valid(form)


def _confirm_viisp_email(
    email_address: str | None,
    user_data: dict[str, str],
    base_url: str,
) -> bool:
    viisp_token_key = ViispTokenKey.objects.first()
    if not viisp_token_key:
        return False
    s = URLSafeSerializer(viisp_token_key.key_content)
    token = s.dumps(
        {
            "personal_code": user_data.get("personal_code"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "email": user_data.get("email"),
            "phone": user_data.get("phone_number"),
            "ticket_id": user_data.get("ticket_id"),
        }
    )
    email(
        [email_address],
        "viisp-confirmation",
        "vitrina/viisp/emails/email_confirmation.md",
        {
            "confirmation_url": "%s%s" % (base_url, reverse("viisp-account-merge", kwargs={"token": token})),
        },
    )
    return True


class ChangeEmailView(TemplateView):
    template_name = "vitrina/viisp/change_email.html"


class LoginFirstView(TemplateView):
    template_name = "vitrina/viisp/login_first.html"


class ConfirmEmailView(TemplateView):
    template_name = "vitrina/viisp/confirm_email.html"


class AccoutnInactiveView(TemplateView):
    template_name = "vitrina/viisp/account_inactive.html"


@method_decorator(csrf_exempt, name="dispatch")
class VIISPAccountMergeView(View):
    def get(self, request, token=None):
        if token:
            if token == "password-set":
                return redirect("password-set")
            viisp_token_key = ViispTokenKey.objects.first()
            if not viisp_token_key:
                return _viisp_api_error(request)
            s = URLSafeSerializer(viisp_token_key.key_content)
            try:
                merge_data_dict = s.loads(token)
            except BadData:
                return redirect("change-email")
            if not isinstance(merge_data_dict, dict):
                return redirect("change-email")
            provider = VIISPProvider(request)
            login = provider.sociallogin_from_response(request, merge_data_dict)
            user = User.objects.filter(email=merge_data_dict.get("email")).first()
            return perform_login(
                request,
                user,
                email_verification=False,
                redirect_url="password-set",
                signal_kwargs={"sociallogin": login},
            )
        return redirect("home")


oauth2_login = OAuth2LoginView.adapter_view(VIISPOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(VIISPOAuth2Adapter)
