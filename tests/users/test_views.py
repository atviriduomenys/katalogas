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
def test_login_with_wrong_credentials(app: DjangoTestApp, user: User):
    form = app.get(reverse('login')).forms[0]
    form['email'] = "test@test.com"
    form['password'] = "wrongpassword"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[credentials_error]]


@pytest.mark.django_db
def test_login_with_correct_credentials(app: DjangoTestApp, user: User):
    form = app.get(reverse('login')).forms[0]
    form['email'] = "test@test.com"
    form['password'] = "test123"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('home')


@pytest.mark.django_db
def test_register_with_short_name(app: DjangoTestApp):
    form = app.get(reverse('register')).forms[0]
    form['first_name'] = "T"
    form['last_name'] = "User"
    form['email'] = "test_@test.com"
    form['password1'] = "test123?"
    form['password2'] = "test123?"
    form['agree_to_terms'] = True
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[name_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_name_with_numbers(app: DjangoTestApp):
    form = app.get(reverse('register')).forms[0]
    form['first_name'] = "T3st"
    form['last_name'] = "User"
    form['email'] = "test_@test.com"
    form['password1'] = "test123?"
    form['password2'] = "test123?"
    form['agree_to_terms'] = True
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[name_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_without_agreeing_to_terms(app: DjangoTestApp):
    form = app.get(reverse('register')).forms[0]
    form['first_name'] = "Test"
    form['last_name'] = "User"
    form['email'] = "test_@test.com"
    form['password1'] = "test123?"
    form['password2'] = "test123?"
    form['agree_to_terms'] = False
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[terms_error]]
    assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_correct_data(app: DjangoTestApp):
    form = app.get(reverse('register')).forms[0]
    form['first_name'] = "Test"
    form['last_name'] = "User"
    form['email'] = "test_@test.com"
    form['password1'] = "test123?"
    form['password2'] = "test123?"
    form['agree_to_terms'] = True
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert User.objects.filter(email='test_@test.com').count() == 1


@pytest.mark.django_db
def test_reset_password_with_wrong_email(app: DjangoTestApp, user: User):
    form = app.get(reverse('reset')).forms[0]
    form['email'] = "wrong.email@test.com"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[reset_error]]
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reset_password_with_correct_email(app: DjangoTestApp, user: User):
    form = app.get(reverse('reset')).forms[0]
    form['email'] = "test@test.com"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
