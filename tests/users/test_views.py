import re
from unittest.mock import patch

import pytest
from allauth.account.models import EmailConfirmation
from django.core import mail
from django.urls import reverse
from django_recaptcha.client import RecaptchaResponse
from django_webtest import DjangoTestApp

from vitrina import settings
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
    form = app.get(reverse('login')).forms['login-form']
    form['email'] = "test@test.com"
    form['password'] = "wrongpassword"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[credentials_error]]


@pytest.mark.django_db
def test_login_with_correct_credentials(app: DjangoTestApp, user: User):
    form = app.get(reverse('login')).forms['login-form']
    form['email'] = "test@test.com"
    form['password'] = "test123"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('home')


@pytest.mark.django_db
def test_register_with_short_name(csrf_exempt_django_app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = csrf_exempt_django_app.post(reverse('register'), {
            'first_name': "T",
            'last_name': "User",
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert list(resp.context['form'].errors.values()) == [[name_error]]
        assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_name_with_numbers(csrf_exempt_django_app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = csrf_exempt_django_app.post(reverse('register'), {
            'first_name': "T3st",
            'last_name': "User",
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert list(resp.context['form'].errors.values()) == [[name_error]]
        assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_without_agreeing_to_terms(csrf_exempt_django_app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = csrf_exempt_django_app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': False,
            "g-recaptcha-response": "PASSED",
        })
        assert list(resp.context['form'].errors.values()) == [[terms_error]]
        assert User.objects.filter(email='test_@test.com').count() == 0


@pytest.mark.django_db
def test_register_with_correct_data(csrf_exempt_django_app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = csrf_exempt_django_app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert resp.status_code == 302
        assert resp.url == reverse('home')
        assert User.objects.filter(email='test_@test.com').count() == 1


@pytest.mark.django_db
def test_reset_password_with_wrong_email(app: DjangoTestApp, user: User):
    form = app.get(reverse('reset')).forms['password-reset-form']
    form['email'] = "wrong.email@test.com"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[reset_error]]
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reset_password_with_correct_email(app: DjangoTestApp, user: User):
    form = app.get(reverse('reset')).forms['password-reset-form']
    form['email'] = "test@test.com"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


@pytest.mark.django_db
def test_change_password_with_no_user(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    resp = app.get(reverse('users-password-change', kwargs={'pk': user1.id}))
    assert resp.url == reverse('login')


@pytest.mark.django_db
def test_change_password_with_wrong_user(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    user2 = User.objects.create_user(email="testas2@testas.com", password="testas123")

    app.set_user(user1)
    resp = app.get(reverse('users-password-change', kwargs={'pk': user2.id}))
    assert resp.url == reverse('user-profile', kwargs={'pk': user1.id})


@pytest.mark.django_db
def test_change_password_with_correct_user(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    app.set_user(user1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "testas123"
    form['new_password1'] = "testavicius1234"
    form['new_password2'] = "testavicius1234"
    resp = form.submit()
    assert resp.url == reverse('user-profile', kwargs={'pk': user1.id})

    form = app.get(reverse('login')).forms['login-form']
    form['email'] = "testas1@testas.com"
    form['password'] = "testavicius1234"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('home')


@pytest.mark.django_db
def test_profile_view_no_login(app: DjangoTestApp, user: User):
    resp = app.get(reverse('user-profile', kwargs={'pk': '1'}))
    assert resp.status_code == 302
    assert resp.location == settings.LOGIN_URL


@pytest.mark.django_db
def test_profile_view_wrong_login(app: DjangoTestApp, user: User):
    app.set_user(user)
    temp_user = User.objects.create_user(email="testas@testas.com", password="testas123")
    resp = app.get(reverse('user-profile', kwargs={'pk': temp_user.pk}))
    assert resp.status_code == 302
    assert str(user.pk) in resp.location


@pytest.mark.django_db
def test_profile_view_correct_login(app: DjangoTestApp, user: User):
    app.set_user(user)
    resp = app.get(reverse('user-profile', kwargs={'pk': user.pk}))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_profile_view_wrong_login(app: DjangoTestApp, user: User):
    app.set_user(user)
    temp_user = User.objects.create_user(email="testas@testas.com", password="testas123")
    resp = app.get(reverse('user-profile', kwargs={'pk': temp_user.pk}))
    assert resp.status_code == 302
    assert str(user.pk) in resp.location


@pytest.mark.django_db
def test_profile_edit_form_no_login(app: DjangoTestApp, user: User):
    resp = app.get(reverse('user-profile-change', kwargs={'pk': '1'}))
    assert resp.status_code == 302
    assert resp.location == settings.LOGIN_URL


@pytest.mark.django_db
def test_profile_edit_form_wrong_login(app: DjangoTestApp, user: User):
    app.set_user(user)
    temp_user = User.objects.create_user(email="testas@testas.com", password="testas123")
    resp = app.get(reverse('user-profile-change', kwargs={'pk': temp_user.pk}))
    assert resp.status_code == 302
    assert str(user.pk) in resp.location


@pytest.mark.django_db
def test_profile_edit_form_correct_login(app: DjangoTestApp):
    user = User.objects.create_user(email="testas@testas.com", password="testas123")
    app.set_user(user)
    form = app.get(reverse('user-profile-change', kwargs={'pk': user.pk})).forms['user-profile-form']
    form['phone'] = '12341234'
    resp = form.submit()
    user.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('user-profile', kwargs={'pk': user.pk})
    assert user.phone == '12341234'


@pytest.mark.django_db
def test_email_confirmation_after_sign_up(csrf_exempt_django_app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        csrf_exempt_django_app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test123@test.com",
            'password1': "somethingverydifficult?",
            'password2': "somethingverydifficult?",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["test123@test.com"]
        assert EmailConfirmation.objects.count() == 1
        assert EmailConfirmation.objects.first().email_address.verified is False

        url = re.search(r'(https?://\S+)', mail.outbox[0].body).group()
        form = csrf_exempt_django_app.get(url).forms['confirm_email_form']
        form.submit()
        assert EmailConfirmation.objects.first().email_address.verified is True

