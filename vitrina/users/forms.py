from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit, ButtonHolder
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm as BasePasswordResetForm, UserCreationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.forms import Form, EmailField, CharField, PasswordInput, BooleanField

from django.utils.translation import gettext_lazy as _

from vitrina.users.models import User


class LoginForm(Form):
    email = EmailField(label=_("El. paštas"), required=True)
    password = CharField(widget=PasswordInput, label=_("Slaptažodis"), required=True)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(Field('email', css_class='input', placeholder=_("El. paštas")),
                    css_class='control'), css_class='field'),
            Div(Div(Field('password', css_class='input', placeholder=_("Slaptažodis")),
                    css_class='control'), css_class='field'),
            ButtonHolder(Submit('submit', _("Prisijungti"), css_class='button is-primary'))
        )

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email is not None and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise ValidationError(_("Neteisingi prisijungimo duomenys"))

        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class RegisterForm(UserCreationForm):
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
        self.helper.layout = Layout(
            Div(Div(Field('first_name', css_class='input', placeholder=_("Vardas")),
                    css_class='control'), css_class='field'),
            Div(Div(Field('last_name', css_class='input', placeholder=_("Pavardė")),
                    css_class='control'), css_class='field'),
            Div(Div(Field('email', css_class='input', placeholder=_("El. paštas")),
                    css_class='control'), css_class='field'),
            Div(Div(Field('password1', css_class='input', placeholder=_("Slaptažodis")),
                    css_class='control'), css_class='field'),
            Div(Div(Field('password2', css_class='input', placeholder=_("Pakartokite slaptažodį")),
                    css_class='control'), css_class='field'),
            Div(Div(Field('agree_to_terms'), css_class='control'), css_class='field'),
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


class PasswordResetForm(BasePasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(Field('email', css_class='input', placeholder=_("El. paštas")),
                    css_class='control'), css_class='field'),
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
        self.helper.layout = Layout(
            Div(Div(Field('new_password1', css_class='input', placeholder=_("Naujas slaptažodis")),
                    css_class='control'), css_class='field'),
            Div(Div(Field('new_password2', css_class='input', placeholder=_("Pakartokite slaptažodį")),
                    css_class='control'), css_class='field'),
            Submit('submit', _("Atstatyti slaptažodį"), css_class='button is-primary'),
        )
