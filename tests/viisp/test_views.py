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
    assert resp.url == '/login/?next=/partner/register/'

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
        'company_code': '1234-5678',
        'company_name': 'test_company',
        'coordinator_phone_number': '+37000000000'
    }
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    form = resp.forms['partner-register-form']
    
    upload_file = open('tests/viisp/resources/test.adoc', 'rb').read()
    form['adoc_file'] = Upload('test.adoc', upload_file)
    form['password'] = "123"
    form['confirm_password'] = "123"
    resp = form.submit()
    org = Organization.objects.filter(company_code='1234-5678').first()
    assert resp.url == '/orgs/{}/'.format(org.id)

@pytest.mark.haystack
def test_form_submit_with_bad_password(app: DjangoTestApp):
    user = UserFactory(
        email="test@testesttesttest.lt",
        password=make_password("123")
    )
    extra_data = {
        'company_code': '1234-5678',
        'company_name': 'test_company',
        'coordinator_phone_number': '+37000000000'
    }
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    form = resp.forms['partner-register-form']
    
    upload_file = open('tests/viisp/resources/test.adoc', 'rb').read()
    form['adoc_file'] = Upload('test.adoc', upload_file)
    form['password'] = "1234"
    form['confirm_password'] = "1234"
    resp = form.submit()
    assert resp.html.find(id='error_1_id_password')

@pytest.mark.haystack
def test_form_submit_with_not_matching_password(app: DjangoTestApp):
    user = UserFactory(
        email="test@testesttesttest.lt",
        password=make_password("123")
    )
    extra_data = {
        'company_code': '1234-5678',
        'company_name': 'test_company',
        'coordinator_phone_number': '+37000000000'
    }
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    form = resp.forms['partner-register-form']
    
    upload_file = open('tests/viisp/resources/test.adoc', 'rb').read()
    form['adoc_file'] = Upload('test.adoc', upload_file)
    form['password'] = "123"
    form['confirm_password'] = "1234"
    resp = form.submit()
    assert resp.html.find(id='error_1_id_confirm_password')

@pytest.mark.haystack
def test_form_submit_with_not_matching_password(app: DjangoTestApp):
    user = UserFactory(
        email="test@testesttesttest.lt",
        password=make_password("123")
    )
    extra_data = {
        'company_code': '1234-5678',
        'company_name': 'test_company',
        'coordinator_phone_number': '+37000000000'
    }
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    form = resp.forms['partner-register-form']
    
    upload_file = open('tests/viisp/resources/test.adoc', 'rb').read()
    form['adoc_file'] = Upload('test.adoc', upload_file)
    form['password'] = "123"
    form['confirm_password'] = "1234"
    resp = form.submit()
    assert resp.html.find(id='error_1_id_confirm_password')

@pytest.mark.haystack
def test_form_submit_with_already_existing_slug(app: DjangoTestApp):
    user = UserFactory(
        email="test@testesttesttest.lt",
        password=make_password("123")
    )
    extra_data = {
        'company_code': '1234-5678',
        'company_name': 'test company',
        'coordinator_phone_number': '+37000000000'
    }
    org = OrganizationFactory(
        slug='tc'
    )
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    form = resp.forms['partner-register-form']
    
    upload_file = open('tests/viisp/resources/test.adoc', 'rb').read()
    form['adoc_file'] = Upload('test.adoc', upload_file)
    form['password'] = "123"
    form['confirm_password'] = "123"
    resp = form.submit()
    assert resp.html.find(id='error_1_id_company_slug')

@pytest.mark.haystack
def test_form_submit_with_nonsense_slug(app: DjangoTestApp):
    user = UserFactory(
        email="test@testesttesttest.lt",
        password=make_password("123")
    )
    extra_data = {
        'company_code': '1234-5678',
        'company_name': 'test company',
        'coordinator_phone_number': '+37000000000'
    }
    org = OrganizationFactory(
        slug='tc'
    )
    temp_user_account = SocialAccount.objects.create(user=user, extra_data=extra_data)
    app.set_user(user)
    resp = app.get(reverse('partner-register'))
    form = resp.forms['partner-register-form']
    
    upload_file = open('tests/viisp/resources/test.adoc', 'rb').read()
    form['adoc_file'] = Upload('test.adoc', upload_file)
    form['password'] = "123"
    form['confirm_password'] = "123"
    form['company_slug'] = 'tč'
    resp = form.submit()
    assert resp.html.find(id='error_1_id_company_slug')
    