import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from django.contrib.auth.hashers import make_password
from vitrina.users.factories import UserFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from allauth.socialaccount.models import SocialAccount
from webtest import Upload


@pytest.mark.haystack
def test_anonymous_user_accesses_data_provider_form(app: DjangoTestApp):
    resp = app.get(reverse('partner-register'))
    assert resp.url == '/login/?next=/accounts/viisp/partner-register/'

@pytest.mark.haystack
def test_logged_in_not_unverified_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    assert resp.url == '/accounts/viisp/login'

@pytest.mark.haystack
def test_logged_in_verified_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory(email="test@test.lt", password="123")
    temp_user_account = SocialAccount.objects.create(user=user)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    assert resp.html.find(id='partner-register-form')

@pytest.mark.haystack
def test_logged_in_coordinator_user_accesses_data_provider_form(app: DjangoTestApp):
    user = UserFactory(email="test@test.lt", password="123")
    extra_data = {
        'company_code': '1234-5678',
        'company_name': 'test_company'
    }
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    assert resp.html.find(id='partner-register-form')


@pytest.mark.haystack
def test_form_submit_with_correct_data(app: DjangoTestApp):
    user = UserFactory(
        email="test@testesttesttest.lt",
        password=make_password("123")
    )
    extra_data = {
        'phone_number': '+37000000000',
        'email': "test@testesttesttest.lt"
    }
    org = OrganizationFactory()
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    form = resp.forms['partner-register-form']

    form['organization'].force_value(org.pk)
    form['request_form'] = Upload('test.doc', b"Test")
    form['coordinator_phone_number'] = '+37000000000'
    resp = form.submit()
    assert resp.url == '/partner/register-complete/'
