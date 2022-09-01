import pytest
from django.core import mail
from django.urls import reverse
from django.test import Client

from vitrina.users.models import User


credentials_error = "Neteisingi prisijungimo duomenys"
name_error = "Vardas ir pavardė negali būti trumpesni nei 3 simboliai, negali turėti skaičių"
email_error = "Naudotojas su tokiu el. pašto adresu jau egzistuoja"
terms_error = "Turite sutikti su naudojimo sąlygomis"
reset_error = "Naudotojas su tokiu el. pašto adresu neegzistuoja"


@pytest.fixture
def user():
    user = User.objects.create_user(email="test@test.com", password="test123")
    return user


@pytest.mark.django_db
def test_login_with_wrong_credentials(client: Client, user: User):
    resp = client.post(reverse('login'), data={'email': "test@test.com", 'password': "wrongpassword"})
    assert list(resp.context['form'].errors.values()) == [[credentials_error]]
    assert resp.wsgi_request.user.is_authenticated is False
    assert resp.wsgi_request.user.pk is None


@pytest.mark.django_db
def test_login_with_correct_credentials(client: Client, user: User):
    resp = client.post(reverse('login'), data={'email': "test@test.com", 'password': "test123"})
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert resp.wsgi_request.user.is_authenticated is True
    assert resp.wsgi_request.user.pk == user.pk


@pytest.mark.django_db
def test_register_with_short_name(client: Client):
    resp = client.post(reverse('register'), data={'first_name': "T", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[name_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_name_with_numbers(client: Client):
    resp = client.post(reverse('register'), data={'first_name': "T3st", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[name_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_existing_email(client: Client, user: User):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[email_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_without_agreeing_to_terms(client: Client):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': False})
    assert list(resp.context['form'].errors.values()) == [[terms_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_correct_data(client: Client):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert User.objects.filter(email='test_@test.com').count() == 1
    assert resp.wsgi_request.user.is_authenticated is True
    assert resp.wsgi_request.user.pk == User.objects.first().pk


@pytest.mark.django_db
def test_reset_password_with_wrong_email(client: Client, user: User):
    resp = client.post(reverse('reset'), data={'email': "wrong.email@test.com"})
    assert list(resp.context['form'].errors.values()) == [[reset_error]]
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reset_password_with_correct_email(client: Client, user: User):
    resp = client.post(reverse('reset'), data={'email': "test@test.com"})
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
