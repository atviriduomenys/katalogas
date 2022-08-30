import pytest
from django.core import mail
from django.urls import reverse
from django.test import Client

from vitrina.users.models import User


@pytest.fixture
def user():
    user = User.objects.create_user(email="test@test.com", password="test123")
    return user


@pytest.mark.django_db
def test_login_with_wrong_credentials(client: Client, user):
    resp = client.post(reverse('login'), data={'email': "test@test.com", 'password': "wrongpassword"})
    assert list(resp.context['form'].errors.values()) == [["Neteisingi prisijungimo duomenys"]]
    assert resp.wsgi_request.user.is_authenticated is False
    assert resp.wsgi_request.user.pk is None


@pytest.mark.django_db
def test_login_with_correct_credentials(client: Client, user):
    resp = client.post(reverse('login'), data={'email': "test@test.com", 'password': "test123"})
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert resp.wsgi_request.user.is_authenticated is True
    assert resp.wsgi_request.user.pk == user.pk


@pytest.fixture
def error_messages():
    name_error = "Vardas ir pavardė negali būti trumpesni nei 3 simboliai, negali turėti skaičių"
    email_error = "Naudotojas su tokiu el. pašto adresu jau egzistuoja"
    password_error = "Slaptažodis turi būti ne trupesnis nei 8 simboliai, jį turi sudaryti raidės " \
                     "ir skaičiai bei specialus simbolis"
    terms_error = "Turite sutikti su naudojimo sąlygomis"
    return {
        'name_error': name_error,
        'email_error': email_error,
        'password_error': password_error,
        'terms_error': terms_error
    }


@pytest.mark.django_db
def test_register_with_short_name(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "T", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[error_messages['name_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_with_name_with_numbers(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "T3st", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[error_messages['name_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_with_existing_email(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[error_messages['email_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_with_short_password(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test1?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[error_messages['password_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_with_password_with_no_letters(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "1234567?", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[error_messages['password_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_with_password_with_no_numbers(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test????", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[error_messages['password_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_with_password_with_no_spec_symbols(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test1234", 'agree_to_terms': True})
    assert list(resp.context['form'].errors.values()) == [[error_messages['password_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_without_agreeing_to_terms(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': False})
    assert list(resp.context['form'].errors.values()) == [[error_messages['terms_error']]]
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_with_correct_data(client: Client, user, error_messages):
    resp = client.post(reverse('register'), data={'first_name': "Test", 'last_name': 'User', 'email': "test_@test.com",
                                                  'password': "test123?", 'agree_to_terms': True})
    resp.status_code = 302
    assert resp.url == reverse('home')
    assert User.objects.count() == 2
    assert resp.wsgi_request.user.is_authenticated is True
    assert resp.wsgi_request.user.pk == User.objects.exclude(pk=user.pk).first().pk


@pytest.mark.django_db
def test_reset_password_with_wrong_email(client: Client, user):
    resp = client.post(reverse('reset'), data={'email': "wrong.email@test.com"})
    resp.status_code = 202
    assert list(resp.context['form'].errors.values()) == [["Naudotojas su tokiu el. pašto adresu neegzistuoja"]]
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reset_password_with_correct_email(client: Client, user):
    resp = client.post(reverse('reset'), data={'email': "test@test.com"})
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
