from allauth.account.forms import LoginForm, SignupForm, ResetPasswordForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
from django.forms import EmailField, CharField, PasswordInput, BooleanField, ModelForm
from django.utils.translation import gettext_lazy as _

from vitrina.users.models import User


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "login-form"
        self.helper.form_action = '/accounts/login/'
        self.helper.layout = Layout(
            Field('login', placeholder=_("El. paštas")),
            Field('password', placeholder=_("Slaptažodis")),
            Field('remember'),
            Submit('submit', _("Prisijungti"), css_class='button is-primary'),
        )


class RegisterForm(SignupForm):
    first_name = CharField(label=_("Vardas"), required=True, )
    last_name = CharField(label=_("Pavardė"), required=True)
    email = EmailField(label=_("El. paštas"), required=True, error_messages={})
    agree_to_terms = BooleanField(label="Sutinku su", required=False)
    password1 = CharField(label=_("Slaptažodis"), strip=False,
                          widget=PasswordInput(attrs={'autocomplete': 'new-password'}))
    password2 = CharField(label=_("Pakartokite slaptažodį"), strip=False,
                          widget=PasswordInput(attrs={'autocomplete': 'new-password'}))

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", 'password1', 'password2', 'agree_to_terms',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "register-form"
        self.helper.layout = Layout(
            Field('first_name', placeholder=_("Vardas")),
            Field('last_name', placeholder=_("Pavardė")),
            Field('email', placeholder=_("El. paštas")),
            Field('password1', placeholder=_("Slaptažodis")),
            Field('password2', placeholder=_("Pakartokite slaptažodį")),
            Field('agree_to_terms'),
            Submit('submit', _("Registruotis"), css_class='button is-primary'),
        )

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name', "")
        last_name = cleaned_data.get('last_name', "")

        if len(first_name) < 3 or not first_name.isalpha():
            self.add_error('first_name',
                           _("Vardas negali būti trumpesnis nei 3 simboliai, negali turėti skaičių"))
        if len(last_name) < 3 or not last_name.isalpha():
            self.add_error('last_name',
                           _("Pavardė negali būti trumpesnė nei 3 simboliai, negali turėti skaičių"))
        if 'agree_to_terms' in cleaned_data and not cleaned_data['agree_to_terms']:
            self.add_error('agree_to_terms', _("Turite sutikti su naudojimo sąlygomis"))
        return cleaned_data


class PasswordResetForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "password-reset-form"
        self.helper.layout = Layout(
            Field('email', placeholder=_("El. paštas")),
            Submit('submit', _("Atstatyti slaptažodį"), css_class='button is-primary'),
        )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', "")
        if email and not User.objects.filter(email=email).exists():
            raise ValidationError(_("Naudotojas su tokiu el. pašto adresu neegzistuoja"))
        return cleaned_data


class PasswordResetConfirmForm(SetPasswordForm):
    new_password1 = CharField(
        label=_("Naujas slaptažodis"),
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False
    )
    new_password2 = CharField(
        label=_("Pakartokite slaptažodį"),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "password-reset-confirm-form"
        self.helper.layout = Layout(
            Field('new_password1', placeholder=_("Naujas slaptažodis")),
            Field('new_password2', placeholder=_("Pakartokite slaptažodį")),
            Submit('submit', _("Atstatyti slaptažodį"), css_class='button is-primary'),
        )


class UserProfileEditForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'organization',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "user-profile-form"
        self.helper.layout = Layout(
                Div(Div(Field('first_name', css_class='input', placeholder=_('Vardas')),
                        css_class='control'), css_class='field'),
                Div(Div(Field('last_name', css_class='input', placeholder=_('Pavardė')),
                        css_class='control'), css_class='field'),
                Div(Div(Field('email', css_class='input', placeholder=_('El. paštas')),
                        css_class='control'), css_class='field'),
                Div(Div(Field('phone', css_class='input', placeholder=_('Telefonas')),
                        css_class='control'), css_class='field'),
                Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )
