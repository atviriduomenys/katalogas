from urllib.parse import urlparse

from django.contrib.contenttypes.models import ContentType
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms import ModelForm, EmailField, ChoiceField, BooleanField, CharField, TextInput, \
    HiddenInput, FileField, PasswordInput, ModelChoiceField, IntegerField, Form, URLField, ModelMultipleChoiceField, \
    DateField, DateInput, Textarea
from django.urls import resolve, Resolver404
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django_select2.forms import ModelSelect2Widget

from vitrina.api.services import is_duplicate_key
from vitrina.fields import FilerImageField
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import get_coordinators_count
from vitrina.plans.models import Plan
from vitrina.viisp.xml_utils import read_adoc_file, parse_adoc_xml_signature_data
from vitrina.users.models import User


class OrganizationUpdateForm(ModelForm):
    company_code = CharField(label=_('Registracijos numeris'), required=True)
    title = CharField(label=_('Pavadinimas'), required=True)
    name = CharField(label=_('Kodinis pavadinimas'), required=True)
    jurisdiction = ModelChoiceField(queryset=Organization.objects.filter(role__isnull=False),
                                    label=_('Jurisdikcija'),
                                    required=True)
    image = FilerImageField(label=_("Paveiksliukas"), required=True, upload_to=Organization.UPLOAD_TO)
    email = CharField(label=_('Elektroninis paštas'), required=True)
    phone = CharField(label=_('Telefono numeris'), required=True)
    address = CharField(label=_('Adresas'), required=True)
    description = CharField(label=_('Aprašymas'), widget=Textarea, required=False)

    class Meta:
        model = Organization
        fields = (
            'company_code',
            'title',
            'name',
            'kind',
            'jurisdiction',
            'image',
            'website',
            'email',
            'phone',
            'address',
            'provider',
            'description',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if org_instance else _("Sukurti")
        parent = self.instance.get_parent()
        if parent:
            self.fields['jurisdiction'].initial = parent
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "organization-form"
        self.helper.layout = Layout(
            Field('company_code', placeholder=_("Registracijos numeris")),
            Field('title', placeholder=_("Pavadinimas")),
            Field('name', placeholder=_('Kodinis pavadinimas')),
            Field('kind', placeholder=_("Tipas")),
            Field('jurisdiction', placeholder=_("Jurisdikcija")),
            Field('image', placeholder=_("Logotipas")),
            Field('website', placeholder=_("Tinklalapis")),
            Field('email', placeholder=_("Elektroninis paštas")),
            Field('phone', placeholder=_("Telefono numeris")),
            Field('address', placeholder=_("Adresas")),
            Field('provider', placeholder=_("Atvėrimo duomenų teikėjas")),
            Field('description', placeholder=_("Aprašymas")),
            Submit('submit', button, css_class='button is-primary')
        )

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            if not name.islower():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti mažoji raidė."))
            elif any((not c.isalnum() and c != '_') for c in name):
                raise ValidationError(_("Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, "
                                        "žodžiai gali būti atskirti _ simboliu,"
                                        "jokie kiti simboliai negalimi."))
            else:
                return name

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.width < 256 or image.height < 256:
                raise ValidationError(_("Nuotraukos dydis turi būti ne mažesnis už 256x256."))
        return image


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
        self.helper.attrs['novalidate'] = ''
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
        self.helper.attrs['novalidate'] = ''
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
    request_form = FileField(label=_("Prašymo forma"))
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
            'request_form'
        ]

    def __init__(self, *args, initial={}, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "partner-register-form"
        self.helper.layout = Layout(
            Field('coordinator_first_name', value=initial.get('coordinator_first_name'), readonly=True),
            Field('coordinator_last_name', value=initial.get('coordinator_last_name'), readonly=True),
            Field('coordinator_phone_number', value=initial.get('coordinator_phone_number') or ''),
            Field('coordinator_email', value=initial.get('coordinator_email'), readonly=True),
            Field('password'),
            Field('confirm_password'),
            Field('company_code', value=initial.get('company_code') or ''),
            Field('company_name', value=initial.get('company_name') or ''),
            Field('company_slug',  value=initial.get('company_slug') or ''),
            Field('request_form'),
            Submit('submit', _("Sukurti"), css_class='button is-primary')
        )

    def clean(self):
        user_email = self.cleaned_data.get('coordinator_email')
        user = User.objects.filter(email=user_email).first()
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        company_slug = self.cleaned_data.get('company_slug')
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
        'organizations': 'organizations',
    }

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        ids = []
        if 'organizations__in' in dependent_fields:
            organizations = dependent_fields.pop('organizations__in')
            ids.extend(organizations)
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)

        provider_orgs = queryset.filter(provider=True).values_list('pk', flat=True)
        ids.extend(provider_orgs)
        queryset = queryset.filter(pk__in=ids)
        return queryset


class OrganizationPlanForm(ModelForm):
    organizations = ModelMultipleChoiceField(queryset=Organization.objects.all(), required=False)
    user_id = IntegerField(widget=HiddenInput(), required=False)
    provider = ModelChoiceField(
        label=_("Paslaugų teikėjas"),
        required=False,
        queryset=Organization.objects.all(),
        widget=ProviderWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0})
    )
    deadline = DateField(
        label=_("Įgyvendinimo terminas"),
        required=False,
        widget=DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Plan
        fields = ('title', 'description', 'deadline', 'provider', 'provider_title',
                  'procurement', 'price', 'project', 'organizations', 'user_id')

    def __init__(self, organizations, user, *args, **kwargs):
        self.organizations = organizations
        self.user = user
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "plan-form"
        self.helper.layout = Layout(
            Field('organizations', css_class="hidden"),
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

        self.initial['organizations'] = self.organizations
        self.initial['user_id'] = self.user.pk

        if not instance:
            if len(self.organizations) == 1:
                self.initial['provider'] = self.organizations[0]
            elif (
                    self.user.organization and
                    self.user.organization.provider and
                    self.user.organization in self.organizations
            ):
                self.initial['provider'] = self.user.organization

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
        self.helper.attrs['novalidate'] = ''
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
