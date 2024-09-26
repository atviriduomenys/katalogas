import pytz
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Submit
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm as BasePasswordResetForm, UserCreationForm, SetPasswordForm, \
    PasswordChangeForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import BooleanField, CharField, EmailField, Form, ModelChoiceField, ModelForm, PasswordInput
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from vitrina import settings
from vitrina.datasets.models import Dataset
from vitrina.fields import DisabledCharField
from vitrina.helpers import email
from vitrina.orgs.models import Organization
from vitrina.users.models import User


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
    captcha = ReCaptchaField(label="", widget=ReCaptchaV2Checkbox(attrs={
        'data-callback': 'onCaptchaClick',
        'data-expired-callback': 'onCaptchaExpire'
    }))

    error_messages = {
        'password_mismatch': _('Slaptažodžio laukai nesutapo'),
    }

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", 'password1', 'password2', 'agree_to_terms', 'captcha')

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
            Field('captcha'),
            Submit('submit', _("Registruotis"), css_class='button is-primary', disabled=True),
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

    def clean_email(self):
        email_address = self.cleaned_data.get('email', '')
        not_allowed_symbols = "!#$%&'*+-/=?^_`{|"
        if email_address:
            if User.objects.filter(email=email_address).exists():
                raise ValidationError(_("Naudotojas su šiuo elektroniniu pašto adresu jau egzistuoja"))
            if email_address[0] in not_allowed_symbols or email_address[-1] in not_allowed_symbols:
                raise ValidationError(_("Įveskite tinkamą el. pašto adresą."))
        return email_address


class RepresentativeRegisterForm(RegisterForm):
    email = EmailField(label=_("El. paštas"), required=True)

    def __init__(self, representative, *args, **kwargs):
        self.representative = representative
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            Field('email', placeholder=_("El. paštas")),
            Field('first_name', placeholder=_("Vardas")),
            Field('last_name', placeholder=_("Pavardė")),
            Field('password1', placeholder=_("Slaptažodis")),
            Field('password2', placeholder=_("Pakartokite slaptažodį")),
            Field('agree_to_terms'),
            Field('captcha'),
            Submit('submit', _("Registruotis"), css_class='button is-primary', disabled=True),
        )

        self.fields["email"].disabled = True
        self.fields["email"].widget.attrs['style'] = "border-color: #767676;"
        self.initial['email'] = self.representative.email


class UserCreationAdminForm(UserCreationForm):
    first_name = CharField(label=_("Vardas"), required=True, )
    last_name = CharField(label=_("Pavardė"), required=True)
    email = EmailField(label=_("Elektroninis pašto adresas"), required=True, error_messages={})
    password1 = CharField(
        label=_("Slaptažodis"),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'})
    )
    password2 = CharField(
        label=_("Slaptažodžio patvirtinimas"),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_("Patikrinimui įveskite tokį patį slaptažodį kaip anksčiau.")
    )

    error_messages = {
        'password_mismatch': _('Slaptažodžio laukai nesutapo'),
    }

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", 'password1', 'password2',)

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
        return cleaned_data

    def clean_email(self):
        email_address = self.cleaned_data.get('email', '')
        not_allowed_symbols = "!#$%&'*+-/=?^_`{|"
        if email_address:
            if User.objects.filter(email=email_address).exists():
                raise ValidationError(_("Naudotojas su šiuo elektroniniu pašto adresu jau egzistuoja"))
            if email_address[0] in not_allowed_symbols or email_address[-1] in not_allowed_symbols:
                raise ValidationError(_("Įveskite tinkamą el. pašto adresą."))
        return email_address


class UserChangeAdminForm(UserChangeForm):
    user_status = CharField(label="")
    first_name = CharField(label=_("Vardas"))
    last_name = CharField(label=_("Pavardė"))
    email = CharField(label=_("Elektroninis paštas"))
    email_confirmed = BooleanField(label=_("Patvirtintas"), required=False)
    organizations_and_roles = DisabledCharField(label=_("Organizacijos ir rolės"), required=False)
    created_date = CharField(label=_("Sukūrimo data"), required=False)
    last_login_date = CharField(label=_("Paskutinį kartą prisijungė"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.instance = instance

        self.fields["organizations_and_roles"].disabled = True
        self.fields["user_status"].disabled = True
        self.fields["user_status"].widget.attrs['style'] = "background-color: #f2f2f2;"
        self.fields["created_date"].disabled = True
        self.fields["created_date"].widget.attrs['style'] = "background-color: #f2f2f2;"
        self.fields["last_login_date"].disabled = True
        self.fields["last_login_date"].widget.attrs['style'] = "background-color: #f2f2f2;"

        if instance:
            tz = pytz.timezone(settings.TIME_ZONE)
            self.initial['created_date'] = instance.created.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
            if instance.last_login:
                self.initial['last_login_date'] = instance.last_login.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
            else:
                self.initial['last_login_date'] = "-"

            self.initial['user_status'] = instance.get_status_display()
            if self.instance.status == User.ACTIVE:
                self.fields["user_status"].widget.attrs['style'] = "background-color: #f2f2f2; color: limegreen;"
            elif self.instance.status == User.AWAITING_CONFIRMATION:
                self.fields["user_status"].widget.attrs['style'] = "background-color: #f2f2f2; color: orange;"
            elif self.instance.status == User.SUSPENDED:
                self.fields["user_status"].widget.attrs['style'] = "background-color: #f2f2f2; color: red;"
                self.fields["first_name"].disabled = True
                self.fields["first_name"].widget.attrs['style'] = "background-color: #f2f2f2;"
                self.fields["last_name"].disabled = True
                self.fields["last_name"].widget.attrs['style'] = "background-color: #f2f2f2;"
                self.fields["email"].disabled = True
                self.fields["email"].widget.attrs['style'] = "background-color: #f2f2f2;"
                self.fields["email_confirmed"].disabled = True
            elif self.instance.status == User.DELETED:
                self.fields["user_status"].widget.attrs['style'] = "background-color: #f2f2f2; color: red;"
                self.fields["first_name"].disabled = True
                self.fields["first_name"].widget.attrs['style'] = "background-color: #f2f2f2;"
                self.fields["last_name"].disabled = True
                self.fields["last_name"].widget.attrs['style'] = "background-color: #f2f2f2;"
                self.fields["email"].disabled = True
                self.fields["email"].widget.attrs['style'] = "background-color: #f2f2f2;"
                self.fields["email_confirmed"].disabled = True
                self.fields["is_active"].disabled = True
                self.fields["is_staff"].disabled = True
                self.fields["is_superuser"].disabled = True
            if instance.emailaddress_set.first() and not instance.emailaddress_set.first().verified:
                self.initial['email_confirmed'] = False
            else:
                self.initial['email_confirmed'] = True

            if reps := instance.representative_set.filter(
                content_type=ContentType.objects.get_for_model(Organization)
            ):
                organizations_and_roles = []
                for rep in reps:
                    organizations_and_roles.append(
                        f"<a href={reverse('admin:vitrina_orgs_representative_change', args=[rep.pk])}>"
                        f"{rep.content_object}, {rep.get_role_display().lower()}"
                        f"</a>"
                    )
                organizations_and_roles = '<br/>'.join(organizations_and_roles)
                self.initial['organizations_and_roles'] = mark_safe(organizations_and_roles)

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
        return cleaned_data

    def clean_email(self):
        email_address = self.cleaned_data.get('email', '')
        not_allowed_symbols = "!#$%&'*+-/=?^_`{|"
        if email_address:
            if User.objects.filter(email=email_address).exclude(pk=self.instance.pk).exists():
                raise ValidationError(_("Naudotojas su šiuo elektroniniu pašto adresu jau egzistuoja"))
            if email_address[0] in not_allowed_symbols or email_address[-1] in not_allowed_symbols:
                raise ValidationError(_("Įveskite tinkamą el. pašto adresą."))
        return email_address


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
        url = "{0}://{1}/reset/{2}/{3}".format(context['protocol'], context['domain'], context['uid'], context['token'])
        email([to_email], 'auth-password-reset-token', "vitrina/email/password_reset.md", {'link': url})


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


class CustomPasswordChangeForm(PasswordChangeForm):
    class Meta:
        model = User
        fields = ("old_password", "new_password1", "new_password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "password-change-form"
        self.helper.layout = Layout(
            Field('old_password', placeholder=_("Senas slaptažodis")),
            Field('new_password1', placeholder=_("Naujas slaptažodis")),
            Field('new_password2', placeholder=_("Pakartokite naują slaptažodį")),
            Submit('submit', _("Patvirtinti keitimą"), css_class='button is-primary'),
        )


class UserProfileEditForm(ModelForm):
    first_name = CharField(label=_("Vardas"), required=True)
    last_name = CharField(label=_("Pavardė"), required=True)
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

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name', "")
        last_name = cleaned_data.get('last_name', "")

        if first_name and len(first_name) < 3 or not first_name.isalpha():
            self.add_error('first_name',
                           _("Vardas negali būti trumpesnis nei 3 simboliai, negali turėti skaičių"))
        if last_name and len(last_name) < 3 or not last_name.isalpha():
            self.add_error('last_name',
                           _("Pavardė negali būti trumpesnė nei 3 simboliai, negali turėti skaičių"))
        return cleaned_data

    def clean_email(self):
        email_address = self.cleaned_data.get('email', '')
        not_allowed_symbols = "!#$%&'*+-/=?^_`{|"
        instance = self.instance if self.instance and self.instance.pk else None
        if email_address:
            if instance and User.objects.filter(email=email_address).exclude(pk=instance.pk).exists():
                raise ValidationError(_("Naudotojas su šiuo elektroniniu pašto adresu jau egzistuoja"))
            if email_address[0] in not_allowed_symbols or email_address[-1] in not_allowed_symbols:
                raise ValidationError(_("Įveskite tinkamą el. pašto adresą."))
        return email_address
