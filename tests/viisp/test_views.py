import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from django.contrib.auth.hashers import make_password

from vitrina.users.factories import UserFactory
from vitrina.orgs.factories import OrganizationFactory
from webtest import Upload


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
def test_fake_viisp_logs_in_existing_user(app: DjangoTestApp):
    settings.debug = True
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
def test_fake_viisp_logs_in_existing_user_no_company_code(app: DjangoTestApp):
    settings.debug = True
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
def test_fake_viisp_logs_in_wrong_password(app: DjangoTestApp):
    settings.debug = True
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
