import base64
from unittest import mock

import pytest
from django.urls import reverse
from django.test import override_settings
from django_webtest import DjangoTestApp
from django.contrib.auth.hashers import make_password

from vitrina.users.factories import UserFactory
from vitrina.users.models import User
from vitrina.orgs.factories import OrganizationFactory
from vitrina.viisp.models import ViispKey, ViispTokenKey
from webtest import Upload


def _seed_viisp_key():
    ViispKey.objects.create(key_content=base64.b64encode(b"dummy-key").decode("ascii"))


def _viisp_user_data(**overrides):
    data = {
        "first_name": "New",
        "last_name": "User",
        "email": "new-viisp-user@example.com",
        "phone_number": "+37060000000",
        "personal_code": "39001010000",
        "proxy_type": "",
        "ticket_id": "ticket-new",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_viisp_complete_login_registers_new_user(app: DjangoTestApp):
    _seed_viisp_key()
    user_data = _viisp_user_data(email="brand-new@example.com", ticket_id="ticket-new-1")

    with mock.patch("vitrina.viisp.views.get_response_with_user_data", return_value=user_data):
        resp = app.post(reverse("viisp-complete-login"), params={"ticket": "ticket-new-1"})

    assert resp.status_code in (200, 302)
    user = User.objects.filter(email="brand-new@example.com").first()
    assert user is not None
    assert user.is_viisp_login is True
    assert user.viisp_company_code is None


@pytest.mark.django_db
def test_viisp_complete_login_new_user_sets_company_code_for_legal_proxy(app: DjangoTestApp):
    _seed_viisp_key()
    user_data = _viisp_user_data(
        email="legal-new@example.com",
        ticket_id="ticket-new-2",
        proxy_type="legal",
        lt_company_code="12345678",
    )

    with mock.patch("vitrina.viisp.views.get_response_with_user_data", return_value=user_data):
        resp = app.post(reverse("viisp-complete-login"), params={"ticket": "ticket-new-2"})

    assert resp.status_code in (200, 302)
    user = User.objects.filter(email="legal-new@example.com").first()
    assert user is not None
    assert user.is_viisp_login is True
    assert user.viisp_company_code == "12345678"


@pytest.mark.django_db
def test_viisp_complete_login_updates_company_code_for_returning_user(app: DjangoTestApp):
    _seed_viisp_key()
    ViispTokenKey.objects.create(key_content="test-secret-key")
    UserFactory(email="returning@example.com", is_viisp_login=False, viisp_company_code=None)
    user_data = _viisp_user_data(
        email="returning@example.com",
        ticket_id="ticket-ret-1",
        proxy_type="legal",
        lt_company_code="87654321",
    )

    with mock.patch("vitrina.viisp.views.get_response_with_user_data", return_value=user_data):
        resp = app.post(reverse("viisp-complete-login"), params={"ticket": "ticket-ret-1"})

    assert resp.status_code == 302
    assert resp.url == reverse("confirm-email")
    user = User.objects.get(email="returning@example.com")
    assert user.is_viisp_login is True
    assert user.viisp_company_code == "87654321"


@pytest.mark.django_db
def test_viisp_login_without_key_renders_error(app: DjangoTestApp):
    # No ViispKey seeded -> must not raise a 500.
    resp = app.post(reverse("viisp-login"), expect_errors=True)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_viisp_login_authenticated_without_token_key_renders_error(app: DjangoTestApp):
    _seed_viisp_key()  # ViispKey present, but no ViispTokenKey
    app.set_user(UserFactory(email="loggedin@example.com"))
    resp = app.post(reverse("viisp-login"), expect_errors=True)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_viisp_complete_login_without_key_renders_error(app: DjangoTestApp):
    # No ViispKey seeded -> must not raise a 500.
    resp = app.post(reverse("viisp-complete-login"), params={"ticket": "t"}, expect_errors=True)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_viisp_complete_login_renders_error_when_soap_call_fails(app: DjangoTestApp):
    _seed_viisp_key()
    with mock.patch("vitrina.viisp.views.get_response_with_user_data", return_value=None):
        resp = app.post(reverse("viisp-complete-login"), params={"ticket": "t"}, expect_errors=True)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_viisp_complete_login_token_without_token_key_renders_error(app: DjangoTestApp):
    _seed_viisp_key()  # ViispKey present, but no ViispTokenKey
    user_data = _viisp_user_data(email="tok@example.com", ticket_id="tok-1")
    with mock.patch("vitrina.viisp.views.get_response_with_user_data", return_value=user_data):
        resp = app.post(
            reverse("viisp-complete-login-token", kwargs={"token": "abc"}),
            params={"ticket": "tok-1"},
            expect_errors=True,
        )
    assert resp.status_code == 200


@pytest.mark.haystack
def test_anonymous_user_accesses_data_provider_form(app: DjangoTestApp):
    resp = app.get(reverse("partner-register"))
    assert resp.url == "/accounts/viisp/login"


@pytest.mark.haystack
def test_logged_in_not_unverified_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resp = app.get(reverse("partner-register"))
    assert resp.url == "/accounts/viisp/login"


@pytest.mark.haystack
def test_logged_in_verified_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory(email="test@test.lt", password="123", is_viisp_login=True)
    app.set_user(user)
    resp = app.get(reverse("partner-register"))
    assert resp.html.find(id="partner-register-form")


@pytest.mark.haystack
def test_form_submit_with_correct_data(app: DjangoTestApp):
    user = UserFactory(email="test@testesttesttest.lt", password=make_password("123"), is_viisp_login=True)
    org = OrganizationFactory()
    app.set_user(user)
    resp = app.get(reverse("partner-register"))
    form = resp.forms["partner-register-form"]

    form["organization"].force_value(org.pk)
    form["request_form"] = Upload("test.doc", b"Test")
    form["coordinator_phone_number"] = "+37000000000"
    resp = form.submit()
    assert resp.url == "/partner/register-complete/"


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_fake_viisp_logs_in_existing_user(app: DjangoTestApp):
    user = UserFactory(email="existing@test.com", is_viisp_login=False)
    user.set_password("abc")
    user.save()
    url = reverse("fake-viisp-complete-login")
    data = {"username": user.email, "password": "abc", "lt_company_code": 12345678, "proxy_type": ""}
    resp = app.post(url, params=data)

    user.refresh_from_db()
    assert user.is_viisp_login is True
    assert user.viisp_company_code == "12345678"
    assert resp.status_code == 302
    assert resp.url == reverse("home")


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_fake_viisp_logs_in_existing_user_no_company_code(app: DjangoTestApp):
    user = UserFactory(email="existing@test.com", is_viisp_login=False, viisp_company_code="123")
    user.set_password("abc")
    user.save()
    url = reverse("fake-viisp-complete-login")
    data = {"username": user.email, "password": "abc"}
    resp = app.post(url, params=data)

    user.refresh_from_db()
    assert user.is_viisp_login is True
    assert user.viisp_company_code is None
    assert resp.status_code == 302
    assert resp.url == reverse("home")


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_fake_viisp_logs_in_wrong_password(app: DjangoTestApp):
    user = UserFactory(email="existing@test.com", is_viisp_login=False)
    user.set_password("abc")
    user.save()
    data = {"username": user.email, "password": "test", "lt_company_code": 12345678, "proxy_type": ""}

    response = app.post(reverse("fake-viisp-complete-login"), params=data)

    assert response.context["form"].errors["__all__"] == [
        (
            "Elektroninis paštas ir/arba slaptažodis yra neteisingas. "
            "Atkreipkite dėmesį, kad abu laukai yra jautrūs raidžių dydžiui (mažosios ir didžiosios raidės)."
        )
    ]


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_fake_viisp_returns_http_404_if_debug_false(app: DjangoTestApp):
    response = app.post(reverse("fake-viisp-complete-login"), params={}, expect_errors=True)

    assert response.status_code == 404
