from unittest.mock import patch

import pytest
from django.http import Http404
from django.urls import reverse
from django_webtest import DjangoTestApp
from django.contrib.auth.hashers import make_password

from vitrina.users.factories import UserFactory
from vitrina.orgs.factories import OrganizationFactory
from allauth.socialaccount.models import SocialAccount
from webtest import Upload
from django.test import override_settings, Client, RequestFactory

from vitrina.viisp.views import FakeVIISPCompleteLoginView


@pytest.mark.haystack
def test_anonymous_user_accesses_data_provider_form(app: DjangoTestApp):
    resp = app.get(reverse("partner-register"))
    assert resp.url == "/login/?next=/accounts/viisp/partner-register/"


@pytest.mark.haystack
def test_logged_in_not_unverified_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resp = app.get(reverse("partner-register"))
    assert resp.url == "/accounts/viisp/login"


@pytest.mark.haystack
def test_logged_in_verified_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory(email="test@test.lt", password="123")
    temp_user_account = SocialAccount.objects.create(user=user)
    app.set_user(user)
    resp = app.get(reverse("partner-register"))
    assert resp.html.find(id="partner-register-form")


@pytest.mark.haystack
def test_logged_in_coordinator_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory(email="test@test.lt", password="123")
    extra_data = {"company_code": "1234-5678", "company_name": "test_company"}
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse("partner-register"))
    assert resp.html.find(id="partner-register-form")


@pytest.mark.haystack
def test_form_submit_with_correct_data(app: DjangoTestApp):
    user = UserFactory(email="test@testesttesttest.lt", password=make_password("123"))
    extra_data = {"phone_number": "+37000000000", "email": "test@testesttesttest.lt"}
    org = OrganizationFactory()
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse("partner-register"))
    form = resp.forms["partner-register-form"]

    form["organization"].force_value(org.pk)
    form["request_form"] = Upload("test.doc", b"Test")
    form["coordinator_phone_number"] = "+37000000000"
    resp = form.submit()
    assert resp.url == "/partner/register-complete/"


@pytest.mark.django_db
def test_fake_viisp_logs_in_existing_user(app: DjangoTestApp):
    user = UserFactory(email="existing@test.com", is_viisp_login=False)
    url = reverse("fake-viisp-complete-login")
    data = {"email": user.email, "lt_company_code": "", "proxy_type": ""}
    resp = app.post(url, params=data, expect_errors=True)

    user.refresh_from_db()
    assert user.is_viisp_login is True
    assert resp.status_code == 302
    assert resp.url == reverse("home")

