from unittest.mock import patch

import pytest
from django.urls import reverse
from django_recaptcha.client import RecaptchaResponse
from django_webtest import DjangoTestApp

from vitrina.users.models import User, OldPassword


@pytest.fixture
def user():
    user = User.objects.create_user(email="test@test.com", password="test123")
    return user


@pytest.mark.django_db
def test_register_minimum_length(app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test@test.com",
            'password1': "Short1!",
            'password2': "Short1!",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert resp.status_code == 200
        assert list(resp.context['form'].errors.values()) == [['Šis slaptažodis yra per trumpas. Jį turi sudaryti bent 12 simbolių.',
                                                               'Slaptažodis per silpnas. Bandykite naudoti daugiau simbolių, didžiųjų raidžių, skaitmenų ir specialiųjų simbolių.']]


@pytest.mark.django_db
def test_register_uppercase(app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test@test.com",
            'password1': "lowercase123456!",
            'password2': "lowercase123456!",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert resp.status_code == 200
        assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudota bent viena didžioji lotyniška raidė (A - Z)."]]


@pytest.mark.django_db
def test_register_lowercase(app: DjangoTestApp):
    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test@test.com",
            'password1': "UPPERCASE123456!",
            'password2': "UPPERCASE123456!",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert resp.status_code == 200
        assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudota bent viena mažoji lotyniška raidė (a - z)."]]


@pytest.mark.django_db
def test_register_digit(app: DjangoTestApp):
    with (patch('django_recaptcha.fields.client.submit') as mocked_submit):
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test@test.com",
            'password1': "NoDigits!!!!!!!!!!!!!",
            'password2': "NoDigits!!!!!!!!!!!!!",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert resp.status_code == 200
        assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudotas bent vienas skaitmuo (0 - 9)."]]


@pytest.mark.django_db
def test_register_special_character(app: DjangoTestApp):
    with (patch('django_recaptcha.fields.client.submit') as mocked_submit):
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = app.post(reverse('register'), {
            'first_name': "Test",
            'last_name': "User",
            'email': "test@test.com",
            'password1': "NoSpecialChar1",
            'password2': "NoSpecialChar1",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        assert resp.status_code == 200
        assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudotas bent vienas specialusis simbolis ( !@#$%^&*()_+-=/.,\';][|}{\":?>< )."]]


@pytest.mark.django_db
def test_password_change_minimum_length(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    app.set_user(user1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "testas123"
    form['new_password1'] = "Short1!"
    form['new_password2'] = "Short1!"
    resp = form.submit()
    assert resp.status_code == 200
    assert list(resp.context['form'].errors.values()) == [["Šis slaptažodis yra per trumpas. Jį turi sudaryti bent 12 simbolių.",
                                                               'Slaptažodis per silpnas. Bandykite naudoti daugiau simbolių, didžiųjų raidžių, skaitmenų ir specialiųjų simbolių.']]


@pytest.mark.django_db
def test_password_change_uppercase(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    app.set_user(user1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "testas123"
    form['new_password1'] = "lowercase123456!"
    form['new_password2'] = "lowercase123456!"
    resp = form.submit()
    assert resp.status_code == 200
    assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudota bent viena didžioji lotyniška raidė (A - Z)."]]


@pytest.mark.django_db
def test_password_change_lowercase(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    app.set_user(user1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "testas123"
    form['new_password1'] = "UPPERCASE123456!"
    form['new_password2'] = "UPPERCASE123456!"
    resp = form.submit()
    assert resp.status_code == 200
    assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudota bent viena mažoji lotyniška raidė (a - z)."]]


@pytest.mark.django_db
def test_password_change_digit(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    app.set_user(user1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "testas123"
    form['new_password1'] = "NoDigits!!!!!!!!!!!!!"
    form['new_password2'] = "NoDigits!!!!!!!!!!!!!"
    resp = form.submit()
    assert resp.status_code == 200
    assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudotas bent vienas skaitmuo (0 - 9)."]]


@pytest.mark.django_db
def test_password_change_special_character(app: DjangoTestApp, user: User):
    user1 = User.objects.create_user(email="testas1@testas.com", password="testas123")
    app.set_user(user1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "testas123"
    form['new_password1'] = "NoSpecialChar1"
    form['new_password2'] = "NoSpecialChar1"
    resp = form.submit()
    assert resp.status_code == 200
    assert list(resp.context['form'].errors.values()) == [["Slaptažodyje turi būti panaudotas bent vienas specialusis simbolis ( !@#$%^&*()_+-=/.,\';][|}{\":?>< )."]]


@pytest.mark.django_db
def test_password_change_not_unique(app: DjangoTestApp):
    user1 = User.objects.create_user(email="test@test.com", password="InitialPassword1!")
    app.set_user(user1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "InitialPassword1!"
    form['new_password1'] = "AgadeBkghf91!"
    form['new_password2'] = "AgadeBkghf91!"
    form.submit()
    user1.refresh_from_db()
    OldPassword.objects.create(user=user1, password=user1.password, version=1)

    for old_password, new_password in [("AgadeBkghf91!", "AgadeBkghf92!"), ("AgadeBkghf92!", "AgadeBkghf93!")]:
        form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
        form['old_password'] = old_password
        form['new_password1'] = new_password
        form['new_password2'] = new_password
        form.submit()
        user1.refresh_from_db()
        OldPassword.objects.create(user=user1, password=user1.password, version=1)

    form = app.get(reverse('users-password-change', kwargs={'pk': user1.id})).forms['password-change-form']
    form['old_password'] = "AgadeBkghf93!"
    form['new_password1'] = "AgadeBkghf92!"
    form['new_password2'] = "AgadeBkghf92!"
    resp = form.submit()

    assert resp.status_code == 200
    assert list(resp.context['form'].errors.values()) == [["Slaptažotis neturi būti toks pat kaip prieš tai 3 buvusieji slaptažodžiai."]]