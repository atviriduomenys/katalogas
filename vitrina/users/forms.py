from datetime import timedelta

import pytz
from allauth.account.models import EmailAddress
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Submit
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import PasswordResetForm as BasePasswordResetForm, UserCreationForm, SetPasswordForm, \
    PasswordChangeForm, UserChangeForm, UsernameField
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BooleanField, CharField, EmailField, Form, ModelChoiceField, ModelForm, PasswordInput, \
    HiddenInput, TextInput
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from django_otp.forms import OTPAuthenticationForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from ipware import get_client_ip

from vitrina import settings
from vitrina.datasets.models import Dataset
from vitrina.fields import DisabledCharField
from vitrina.helpers import email
from vitrina.orgs.models import Organization
from vitrina.users.models import User, UserEmailDevice


class LoginForm(OTPAuthenticationForm):
    username = UsernameField(widget=TextInput(attrs={'autofocus': True}), label=_("El. paštas"))
    otp_token = CharField(
        required=False, widget=TextInput(attrs={'autocomplete': 'off'}),
        label=_("Vienkartinis prisijungimo kodas")
    )

    otp_error_messages = {
        'token_required': _('Įveskite prisijungimo kodą.'),
        'challenge_exception': _('Klaida generuojant vienkartinį kodą.'),
        'not_interactive': _('Pasirinktas prisijungimo patvirtinimo metodas neinteraktyvus.'),
        'challenge_message': _('Dėmesio. Kadangi jūsų įrenginys nebuvo atpažintas, reikalingas papildomas '
                               'patvirtinimas. Prašome įrašyti vienkartinį kodą, išsiųstą el. paštu.'),
        'invalid_token': _('Neteisingas kodas. Įsitikinkite, kad įvedėtę teisingą kodą.'),
        'n_failed_attempts': _("Prisijungimo patvirtinimas laikimai negalimas dėl %(failure_count)d "
                               "nesėkmingų bandymų prisijungti."),
        'verification_not_allowed': _("Prisijungimo patvirtinimas laikimai negalimas."),
    }

    error_messages = {
        'invalid_login': _("Neteisingi prisijungimo duomenys"),
        'inactive': _("Ši paskyra neaktyvi."),
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "login-form"
        self.helper.form_action = '.'
        self.helper.layout = Layout(
            Field('username', placeholder=_("El. paštas")),
            Field('password', placeholder=_("Slaptažodis")),
            Field('otp_token'),
            Field('otp_challenge'),
            Submit('submit', _("Prisijungti"), css_class='button is-primary'),
        )

        self.fields['otp_device'].widget = HiddenInput()

    def _chosen_device(self, user):
        client_ip, _ = get_client_ip(self.request)
        user_agent = self.request.headers.get('User-Agent', '')

        device = UserEmailDevice.objects.filter(
            user=user.pk,
            ip_address=client_ip,
            user_agent=user_agent
        ).first()

        if not device:
            device = UserEmailDevice.objects.create(
                user=user,
                name=str(user),
                ip_address=client_ip,
                user_agent=user_agent
            )
        return device

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)

            if self.user_cache and username:
                user_email = EmailAddress.objects.filter(email=username).first()
                if (user_email and not user_email.verified) or self.user_cache.status == User.AWAITING_CONFIRMATION:
                    self.user_cache = None
                    raise ValidationError(_("El. pašto adresas nepatvirtintas. "
                                            "Patvirtinti galite sekdami nuoroda išsiųstame laiške."))

            user = User.objects.filter(email=username).first()
            if user:
                if (
                    user.status == User.LOCKED and
                    user.failed_login_attempts < 5 and
                        (user.password_last_updated is None or
                         user.password_last_updated > now() - timedelta(days=90))
                ):
                    self.user_cache = None
                    raise ValidationError(_('Jūsų paskyra užblokuota. Norėdami prisijungti, turite atkurti '
                                            'slaptažodį per "Atstatyti slaptažodį".'))

                if user.failed_login_attempts >= 5:
                    self.user_cache = None
                    if user.status != User.LOCKED:
                        user.lock_user()
                    raise ValidationError(_('Jūs viršijote leistinų slaptažodžio įvedimo bandymų skaičių. '
                                            'Po 5 nesėkmingų bandymų jūsų paskyra buvo užblokuota dėl '
                                            'saugumo priežasčių. Norėdami vėl prisijungti, turite atkurti slaptažodį '
                                            'per "Atstatyti slaptažodį".'))

                if user.password_last_updated is None or user.password_last_updated < now() - timedelta(days=90):
                    self.user_cache = None
                    if user.status != User.LOCKED:
                        user.lock_user()
                    raise ValidationError(_('Jūsų slaptažodžio galiojimas baigėsi. Norėdami prisijungti, '
                                            'turite atkurti slaptažodį per "Atstatyti slaptažodį". '))

            if self.user_cache is None:
                if user:
                    user.failed_login_attempts += 1
                    user.save()
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        user = self.user_cache
        device = self._chosen_device(user)

        if device and device.last_used_at:
            # if device exists and has been used, we allow login without otp validation
            pass
        else:
            self.clean_otp(user)
        return self.cleaned_data


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
    password1 = CharField(
        label=_("Atnaujinti slaptažodį"),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False
    )
    password2 = CharField(
        label=_("Pakartoti slatažodį"),
        strip=False,
        widget=PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False
    )

    error_messages = {
        'password_mismatch': _('Slaptažodžio laukai nesutapo'),
    }

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
            if instance.status != User.ACTIVE and instance.status != User.LOCKED:
                if 'password1' in self.fields:
                    self.fields['password1'].widget = HiddenInput()
                if 'password' in self.fields:
                    self.fields['password2'].widget = HiddenInput()

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
            elif self.instance.status == User.LOCKED:
                self.fields["user_status"].widget.attrs['style'] = "background-color: #f2f2f2; color: grey;"
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

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get('password1')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password1', error)

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password1'):
            user.unlock_user()
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


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
        if (
            email and
            not User.objects.filter(Q(email=email) & Q(Q(status=User.LOCKED) | Q(status=User.ACTIVE))).exists()
        ):
            raise ValidationError(_("Naudotojas su tokiu el. pašto adresu neegzistuoja arba yra neaktyvus"))
        return cleaned_data

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        url = "{0}://{1}/reset/{2}/{3}".format(context['protocol'], context['domain'], context['uid'], context['token'])
        email([to_email], 'auth-password-reset-token', "vitrina/email/password_reset.md", {'link': url})


class PasswordResetConfirmForm(SetPasswordForm):
    error_messages = {
        'password_mismatch': _('Slaptažodžiai nesutampa. Pabandykite įvesti dar kartą.'),
    }
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
