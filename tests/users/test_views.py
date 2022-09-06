import pytest
from django.core import mail
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.users.models import User


credentials_error = "Neteisingi prisijungimo duomenys"
name_error = "Vardas negali būti trumpesnis nei 3 simboliai, negali turėti skaičių"
terms_error = "Turite sutikti su naudojimo sąlygomis"
reset_error = "Naudotojas su tokiu el. pašto adresu neegzistuoja"


@pytest.fixture
def user():
    user = User.objects.create_user(email="test@test.com", password="test123")
    return user


@pytest.mark.django_db
def test_login_with_wrong_credentials(csrf_exempt_django_app: DjangoTestApp, user: User):
    resp = csrf_exempt_django_app.post(reverse('login'), {
        'email': "test@test.com",
        'password': "wrongpassword"
    })
    assert list(resp.context['form'].errors.values()) == [[credentials_error]]


@pytest.mark.django_db
def test_login_with_correct_credentials(csrf_exempt_django_app: DjangoTestApp, user: User):
    resp = csrf_exempt_django_app.post(reverse('login'), {
        'email': "test@test.com",
        'password': "test123"
    })
    assert resp.status_code == 302
    assert resp.url == reverse('home')


@pytest.mark.django_db
def test_register_with_short_name(csrf_exempt_django_app: DjangoTestApp):
    resp = csrf_exempt_django_app.post(reverse('register'), {
        'first_name': "T",
        'last_name': 'User',
        'email': "test_@test.com",
        'password1': "test123?",
        'password2': "test123?",
        'agree_to_terms': True
    })
    assert list(resp.context['form'].errors.values()) == [[name_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_name_with_numbers(csrf_exempt_django_app: DjangoTestApp):
    resp = csrf_exempt_django_app.post(reverse('register'), {
        'first_name': "T3st",
        'last_name': 'User',
        'email': "test_@test.com",
        'password1': "test123?",
        'password2': "test123?",
        'agree_to_terms': True
    })
    assert list(resp.context['form'].errors.values()) == [[name_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_without_agreeing_to_terms(csrf_exempt_django_app: DjangoTestApp):
    resp = csrf_exempt_django_app.post(reverse('register'), {
        'first_name': "Test",
        'last_name': 'User',
        'email': "test_@test.com",
        'password1': "test123?",
        'password2': "test123?",
        'agree_to_terms': False
    })
    assert list(resp.context['form'].errors.values()) == [[terms_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_correct_data(csrf_exempt_django_app: DjangoTestApp):
    resp = csrf_exempt_django_app.post(reverse('register'), {
        'first_name': "Test",
        'last_name': 'User',
        'email': "test_@test.com",
        'password1': "test123?",
        'password2': "test123?",
        'agree_to_terms': True
    })
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert User.objects.filter(email='test_@test.com').count() == 1


@pytest.mark.django_db
def test_reset_password_with_wrong_email(csrf_exempt_django_app: DjangoTestApp, user: User):
    resp = csrf_exempt_django_app.post(reverse('reset'), {'email': "wrong.email@test.com"})
    assert list(resp.context['form'].errors.values()) == [[reset_error]]
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reset_password_with_correct_email(csrf_exempt_django_app: DjangoTestApp, user: User):
    resp = csrf_exempt_django_app.post(reverse('reset'), {'email': "test@test.com"})
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
