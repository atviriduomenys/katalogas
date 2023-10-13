from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm as BasePasswordResetForm, UserCreationForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import Form, EmailField, CharField, PasswordInput, BooleanField, ModelForm, ModelChoiceField

from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.users.models import User
from vitrina.helpers import buttons, submit
from vitrina.helpers import prepare_email_by_identifier
from django.core.mail import send_mail


class LoginForm(Form):
    email = EmailField(label=_("El. paštas"), required=True)
    password = CharField(widget=PasswordInput, label=_("Slaptažodis"), required=True)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "login-form"
        self.helper.layout = Layout(
            Field('email', placeholder=_("El. paštas")),
            Field('password', placeholder=_("Slaptažodis")),
            Submit('submit', _("Prisijungti"), css_class='button is-primary'),
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
    agree_to_terms = BooleanField(label=_("Sutinku su"), required=False)
    password1 = CharField(label=_("Slaptažodis"), strip=False,
                          widget=PasswordInput(attrs={'autocomplete': 'new-password'}))
    password2 = CharField(label=_("Pakartokite slaptažodį"), strip=False,
                          widget=PasswordInput(attrs={'autocomplete': 'new-password'}))

    error_messages = {
        'password_mismatch': _('Slaptažodžio laukai nesutapo'),
    }

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", 'password1', 'password2', 'agree_to_terms',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
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


class PasswordSetForm(ModelForm):
    password = CharField(label=_("Slaptažodis"), strip=False,
                    widget=PasswordInput(attrs={'autocomplete': 'new-password'}), validators=[validate_password])
    confirm_password = CharField(label=_("Pakartokite slaptažodį"), strip=False,
                    widget=PasswordInput(attrs={'autocomplete': 'new-password'}))
    
    class Meta:
        model = User
        fields = [
            'password',
            'confirm_password'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "password-set-form"
        self.helper.layout = Layout(
            Field('password', placeholder=_("Slaptažodis")),
            Field('confirm_password', placeholder=_("Pakartokite slaptažodį")),
            Submit('submit', _("Pakeisti slatažodį"), css_class='button is-primary')
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class PasswordResetForm(BasePasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
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

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        base_email_template = """Sveiki, norėdami susikurti naują slaptažodį turite paspausti šią nuorodą: {0}/
        """
        url = "{0}://{1}/reset/{2}/{3}".format(context['protocol'], context['domain'], context['uid'], context['token'])
        email_data = prepare_email_by_identifier('auth-password-reset-token', base_email_template,
                                                 'Slaptazodzio atstatymas',
                                                 [url])
        send_mail(
            subject=_(email_data['email_subject']),
            message=_(email_data['email_content']),
            from_email=from_email,
            recipient_list=[to_email],
        )


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
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "password-reset-confirm-form"
        self.helper.layout = Layout(
            Field('new_password1', placeholder=_("Naujas slaptažodis")),
            Field('new_password2', placeholder=_("Pakartokite slaptažodį")),
            Submit('submit', _("Atstatyti slaptažodį"), css_class='button is-primary'),
        )


class UserProfileEditForm(ModelForm):
    first_name = CharField(label=_("Vardas"), required=False)
    last_name = CharField(label=_("Pavardė"), required=False)
    phone = CharField(label=_("Telefonas"), required=False)
    email = EmailField(label=_("El. paštas"), required=True)
    organization = ModelChoiceField(label=_("Organizacija"), required=False, queryset=Organization.public.all())

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
        self.helper.attrs['novalidate'] = ''
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
                Field('organization'),
                Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )

        user = self.instance if self.instance and self.instance.pk else None
        if user:
            organization_ids = []
            if user.organization:
                organization_ids.append(user.organization.pk)

            organization_rep_ids = user.representative_set.filter(
                content_type=ContentType.objects.get_for_model(Organization)
            ).values_list('object_id', flat=True)

            dataset_rep_ids = user.representative_set.filter(
                content_type=ContentType.objects.get_for_model(Dataset)
            ).values_list('object_id', flat=True)
            dataset_rep_ids = Dataset.objects.filter(pk__in=dataset_rep_ids).values_list('organization__pk', flat=True)

            organization_ids.extend(organization_rep_ids)
            organization_ids.extend(dataset_rep_ids)

            self.fields['organization'].queryset = self.fields['organization'].queryset.filter(pk__in=organization_ids)
