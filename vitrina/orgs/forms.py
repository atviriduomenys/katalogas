from urllib.parse import urlparse

from django.contrib.contenttypes.models import ContentType
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms import ModelForm, EmailField, ChoiceField, BooleanField, CharField, TextInput, \
    HiddenInput, FileField, PasswordInput, ModelChoiceField, IntegerField, Form, URLField
from django.urls import resolve, Resolver404
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django_select2.forms import ModelSelect2Widget

from vitrina.api.services import is_duplicate_key
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import get_coordinators_count
from vitrina.plans.models import Plan
from vitrina.viisp.xml_utils import read_adoc_file, parse_adoc_xml_signature_data
from vitrina.users.models import User

class RepresentativeUpdateForm(ModelForm):
    role = ChoiceField(label=_("Rolė"), choices=Representative.ROLES)
    has_api_access = BooleanField(label=_("Suteikti API prieigą"), required=False)
    api_key = CharField(
        label=_("API raktas"),
        required=False,
        widget=TextInput(attrs={'readonly': True, 'style': 'padding-left: 0'})
    )
    regenerate_api_key = BooleanField(label=_("Pergeneruoti raktą"), required=False)

    object_model = Organization

    class Meta:
        model = Representative
        fields = ('role', 'has_api_access', 'api_key', 'regenerate_api_key',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Field('role'),
            Field('has_api_access'),
            Field('regenerate_api_key'),
            Field('api_key', css_class="is-borderless"),
            Submit('submit', _("Redaguoti"), css_class='button is-primary'),
        )
        if self.instance.has_api_access and self.instance.apikey_set.exists():
            api_key = self.instance.apikey_set.first().api_key
            self.initial['api_key'] = api_key

            org, is_duplicate = is_duplicate_key(api_key)
            if is_duplicate:
                self.fields['api_key'].widget = TextInput(attrs={
                    'style': 'text-decoration: line-through; padding-left: 0',
                    'readonly': True
                })
                self.fields['api_key'].help_text = mark_safe(
                    f'<p class="help" style="color: red;">{_("Raktas yra negaliojantis")}</p>'
                )

        else:
            self.fields['api_key'].widget = HiddenInput()

    def clean(self):
        role = self.cleaned_data.get('role')
        if (
            self.instance.role == Representative.COORDINATOR and
            role != Representative.COORDINATOR and
            get_coordinators_count(
                self.object_model,
                self.instance.object_id,
            ) == 1
        ):
            raise ValidationError(_(
                "Negalima panaikinti koordinatoriaus rolės naudotojui, "
                "jei tai yra vienintelis koordinatoriaus rolės atstovas."
            ))
        return self.cleaned_data


class RepresentativeCreateForm(ModelForm):
    email = EmailField(label=_("El. paštas"))
    role = ChoiceField(label=_("Rolė"), choices=Representative.ROLES)
    has_api_access = BooleanField(label=_("Suteikti API prieigą"), required=False)

    object_model = Organization
    object_id: int

    class Meta:
        model = Representative
        fields = ('email', 'role', 'has_api_access')

    def __init__(self, object_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_id = object_id
        self.helper = FormHelper()
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Field('email'),
            Field('role'),
            Field('has_api_access'),
            Submit('submit', _("Sukurti"), css_class='button is-primary'),
        )

    def clean(self):
        email = self.cleaned_data.get('email')
        content_type = ContentType.objects.get_for_model(self.object_model)
        if (
            Representative.objects.
            filter(
                content_type=content_type,
                object_id=self.object_id,
                email=email
            ).
            exists()
        ):
            self.add_error('email', _(
                "Narys su šiuo el. pašto adresu jau egzistuoja."
            ))
        return super().clean()

class PartnerRegisterForm(ModelForm):
    coordinator_email = EmailField(label=_("Koordinatoriaus el. paštas"))
    coordinator_first_name = CharField(label=_("Koordinatoriaus vardas"))
    coordinator_last_name = CharField(label=_("Koordinatoriaus pavardė"))
    coordinator_phone_number = CharField(label=_("Koordinatoriaus telefono numeris"))
    password = CharField(label=_("Slaptažodis"), strip=False,
            widget=PasswordInput(attrs={'autocomplete': 'new-password'}))
    confirm_password = CharField(label=_("Pakartokite slaptažodį"), strip=False,
            widget=PasswordInput(attrs={'autocomplete': 'new-password'}))
    company_code = CharField(label=_("Organizacijos kodas"))
    company_name = CharField(label=_("Organizacijos pavadinimas"))
    company_slug = CharField(label=_("Organizacijos trumpinys"), validators=[validate_slug])
    adoc_file = FileField(label=_("Adoc failas"))
    class Meta:
        model = Organization
        fields = [
            'coordinator_first_name',
            'coordinator_last_name',
            'coordinator_phone_number',
            'coordinator_email',
            'password',
            'confirm_password',
            'company_code',
            'company_name',
            'company_slug',
            'adoc_file'
        ]

    def __init__(self, *args, initial={}, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "partner-register-form"
        self.helper.layout = Layout(
            Field('coordinator_first_name', value=initial.get('coordinator_first_name'), readonly=True),
            Field('coordinator_last_name', value=initial.get('coordinator_last_name'), readonly=True),
            Field('coordinator_phone_number', value=initial.get('coordinator_phone_number'), readonly=True),
            Field('coordinator_email', value=initial.get('coordinator_email'), readonly=True),
            Field('password'),
            Field('confirm_password'),
            Field('company_code', value=initial.get('company_code'), readonly=True),
            Field('company_name', value=initial.get('company_name'), readonly=True),
            Field('company_slug',  value=initial.get('company_slug'), readonly=initial.get('company_slug_read_only')),
            Field('adoc_file'),
            Submit('submit', _("Sukurti"), css_class='button is-primary')
        )

    def clean(self):
        user_email = self.cleaned_data.get('coordinator_email')
        user = User.objects.filter(email=user_email).first()
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        file = self.cleaned_data.get('adoc_file')
        file_contents = read_adoc_file(file)
        sa_company_codes = parse_adoc_xml_signature_data(file_contents)
        company_code = self.cleaned_data.get('company_code')
        company_slug = self.cleaned_data.get('company_slug')
       # if company_code not in sa_company_codes:
       #     self.add_error('adoc_file', _(
       #     "Failas nepasirašytas arba blogai pasirašytas."
       # ))
        if (
            Organization.objects.
            filter(
                slug=company_slug
            ).
            exists()
        ):
            self.add_error('company_slug', _(
                "Organizacija šiuo trumpiniu jau egzistuoja."
            ))
        elif password != confirm_password:
            self.add_error('confirm_password', _(
            "Slaptažodžiai nesutampa"
        )) 
        elif not user.check_password(password):
            self.add_error('password', _(
            "Neteisingas slaptažodis"
        ))
        return self.cleaned_data


class ProviderWidget(ModelSelect2Widget):
    model = Organization
    search_fields = ['title__icontains']
    dependent_fields = {
        'organization_id': 'organization_id',
        'user_id': 'user_id'
    }

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        ids = []
        if 'organization_id' in dependent_fields:
            organization_id = dependent_fields.pop('organization_id')
            ids.append(organization_id)
        if 'user_id' in dependent_fields:
            user_id = dependent_fields.pop('user_id')
            try:
                user = User.objects.get(pk=user_id)
            except ObjectDoesNotExist:
                user = None
            if user and user.organization:
                ids.append(user.organization.pk)
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)

        provider_orgs = queryset.filter(provider=True).values_list('pk', flat=True)
        ids.extend(provider_orgs)
        queryset = queryset.filter(pk__in=ids)
        return queryset


class OrganizationPlanForm(ModelForm):
    organization_id = IntegerField(widget=HiddenInput)
    user_id = IntegerField(widget=HiddenInput)
    provider = ModelChoiceField(
        label=_("Paslaugų teikėjas"),
        required=False,
        queryset=Organization.objects.all(),
        widget=ProviderWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0})
    )

    class Meta:
        model = Plan
        fields = ('title', 'description', 'deadline', 'provider', 'provider_title',
                  'procurement', 'price', 'project', 'organization_id', 'user_id')

    def __init__(self, organization, user, *args, **kwargs):
        self.organization = organization
        self.user = user
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.form_id = "plan-form"
        self.helper.layout = Layout(
            Field('organization_id'),
            Field('user_id'),
            Field('title'),
            Field('description'),
            Field('deadline'),
            Field('provider'),
            Field('provider_title'),
            Field('procurement'),
            Field('price'),
            Field('project'),
            Submit('submit', _('Redaguoti') if instance else _("Sukurti"), css_class='button is-primary'),
        )

        self.initial['organization_id'] = self.organization.pk
        self.initial['user_id'] = self.user.pk

        if not instance:
            if self.user.organization and self.user.organization.provider:
                self.initial['provider'] = self.user.organization
            else:
                self.initial['provider'] = self.organization

    def clean(self):
        provider = self.cleaned_data.get('provider')
        provider_title = self.cleaned_data.get('provider_title')

        if provider and provider_title:
            self.add_error(
                'provider',
                _('Turi būti nurodytas arba paslaugų teikėjas, arba paslaugų teikėjo pavadinimas, bet ne abu.')
            )
        elif not provider and not provider_title:
            self.add_error(
                'provider',
                _('Turi būti nurodytas paslaugų teikėjas arba paslaugų teikėjo pavadinimas.')
            )


class OrganizationMergeForm(Form):
    organization = URLField(
        label=_("Organizacija"),
        help_text=_("Nurodykite pilną nuorodą į organizaciją, su kuria norite sujungti"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "merge-form"
        self.helper.layout = Layout(
            Field('organization'),
            Submit('submit', _("Tęsti"), css_class='button is-primary')
        )

    def clean_organization(self):
        organization = self.cleaned_data.get('organization')
        if organization:
            url = urlparse(organization)
            try:
                url = resolve(url.path)
            except Resolver404:
                raise ValidationError(_("Organizacija su šia nuoroda nerasta."))
            if (
                url.url_name != 'organization-detail' or
                not Organization.objects.filter(pk=url.kwargs.get('pk'))
            ):
                raise ValidationError(_("Organizacija su šia nuoroda nerasta."))
            else:
                return url.kwargs.get('pk')
        return organization
