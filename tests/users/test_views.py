from django.core import mail
from django.urls import reverse
from django_webtest import WebTest

from vitrina.users.models import User


credentials_error = "Neteisingi prisijungimo duomenys"
name_error = "Vardas negali būti trumpesnis nei 3 simboliai, negali turėti skaičių"
email_error = "Naudotojas su tokiu el. pašto adresu jau egzistuoja"
terms_error = "Turite sutikti su naudojimo sąlygomis"
reset_error = "Naudotojas su tokiu el. pašto adresu neegzistuoja"


class UserAuthTest(WebTest):
    csrf_checks = False

    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="test123")


class LoginTest(UserAuthTest):
    def test_with_wrong_credentials(self):
        resp = self.client.post(reverse('login'), {'email': "test@test.com", 'password': "wrongpassword"})
        self.assertEqual(list(resp.context['form'].errors.values()), [[credentials_error]])
        self.assertFalse(resp.wsgi_request.user.is_authenticated)
        self.assertIsNone(resp.wsgi_request.user.pk)

    def test_with_correct_credentials(self):
        resp = self.client.post(reverse('login'), {'email': "test@test.com", 'password': "test123"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('home'))
        self.assertTrue(resp.wsgi_request.user.is_authenticated)
        self.assertEqual(resp.wsgi_request.user.pk, self.user.pk)


class RegisterTest(UserAuthTest):
    def test_with_short_name(self):
        resp = self.client.post(reverse('register'), {
            'first_name': "T",
            'last_name': 'User',
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': True
        })
        self.assertEqual(list(resp.context['form'].errors.values()), [[name_error]])
        self.assertEqual(User.objects.filter(email='test_@test.com').count(), 0)

    def test_with_name_with_numbers(self):
        resp = self.client.post(reverse('register'), {
            'first_name': "T3st",
            'last_name': 'User',
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': True
        })
        self.assertEqual(list(resp.context['form'].errors.values()), [[name_error]])
        self.assertEqual(User.objects.filter(email='test_@test.com').count(), 0)

    def test_without_agreeing_to_terms(self):
        resp = self.client.post(reverse('register'), {
            'first_name': "Test",
            'last_name': 'User',
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': False
        })
        self.assertEqual(list(resp.context['form'].errors.values()), [[terms_error]])
        self.assertEqual(User.objects.filter(email='test_@test.com').count(), 0)

    def test_with_correct_data(self):
        resp = self.client.post(reverse('register'), {
            'first_name': "Test",
            'last_name': 'User',
            'email': "test_@test.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': True
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('home'))
        self.assertEqual(User.objects.filter(email='test_@test.com').count(), 1)
        self.assertTrue(resp.wsgi_request.user.is_authenticated)
        self.assertEqual(resp.wsgi_request.user.pk, User.objects.filter(email='test_@test.com').first().pk)


class PasswordResetTest(UserAuthTest):
    def test_with_wrong_email(self):
        resp = self.client.post(reverse('reset'), {'email': "wrong.email@test.com"})
        self.assertEqual(list(resp.context['form'].errors.values()), [[reset_error]])
        self.assertEqual(len(mail.outbox), 0)

    def test_with_correct_email(self):
        resp = self.client.post(reverse('reset'), {'email': "test@test.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('home'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
