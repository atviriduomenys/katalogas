import secrets
from urllib.parse import urlparse
import re

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q
from django.forms import ModelForm, EmailField, ChoiceField, BooleanField, CharField, \
    HiddenInput, FileField, ModelChoiceField, IntegerField, Form, URLField, ModelMultipleChoiceField, \
    DateField, DateInput, Textarea, CheckboxInput
from django.forms.models import ModelChoiceIterator
from django.urls import resolve, Resolver404
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget

from vitrina.api.models import ApiKey, ApiScope
from vitrina.datasets.models import Dataset
from vitrina.fields import FilerImageField, TranslatedFileField, TranslatedFileInput
from vitrina.helpers import validate_file
from vitrina.messages.models import Subscription
from vitrina.orgs.models import Organization, Representative, RepresentativeRequest, Template
from vitrina.orgs.services import get_coordinators_count
from vitrina.plans.models import Plan
from vitrina.structure.services import get_data_from_spinta
from vitrina.structure.models import Metadata


class ChoiceFieldRequiredValidationOnly(ModelChoiceField):
    def validate(self, value):
        if not value:
            raise ValidationError(_("Šis laukas yra privalomas."))

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            key = self.to_field_name or 'pk'
            if isinstance(value, self.queryset.model):
                value = getattr(value, key)
            value = self.queryset.get(**{key: value})
        except self.queryset.model.DoesNotExist:
            pass
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return value


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


def get_organization_queryset(jar_model_uri, jar_query_uri, value, queryset=None):
    if queryset is None:
        queryset = Organization.objects.none()
    data = get_data_from_spinta(
        model=jar_model_uri,
        query=jar_query_uri.format(value)
    ).get('_data', [])
    org_list = [Organization(
        id=item.get('ja_kodas'),
        title=item.get('ja_pavadinimas'),
        company_code=item.get('ja_kodas'),
        address=item.get('pilnas_adresas')

    ) for item in data]
    if org_list:
        if queryset._result_cache is None:
            queryset._result_cache = []
        queryset._result_cache.extend(org_list)
    return queryset


class OrganizationWidget(ModelSelect2Widget):
    model = Organization
    search_fields = ['title__icontains']
    max_results = 10
    jar_model_uri = 'datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo'
    jar_query_uri_title = "ja_pavadinimas.contains('{}')"
    jar_query_uri_code = "ja_kodas={}"

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)
        if term:
            if len(queryset) == 0:
                queryset = get_organization_queryset(
                    self.jar_model_uri,
                    self.jar_query_uri_title,
                    term,
                    queryset
                )
                self.queryset = queryset
        return queryset

    def optgroups(self, name, value, attrs=None):
        """Return only selected options and set QuerySet from `ModelChoicesIterator`."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value}
        if not self.is_required and not self.allow_multiple_selected:
            default[1].append(self.create_option(name, "", "", False, 0))
        if not isinstance(self.choices, ModelChoiceIterator):
            return super().optgroups(name, value, attrs=attrs)
        selected_choices = {
            c for c in selected_choices if c not in self.choices.field.empty_values
        }
        field_name = self.choices.field.to_field_name or "pk"
        query = Q(**{"%s__in" % field_name: selected_choices})
        queryset = self.choices.queryset.filter(query)
        if selected_choices and not queryset:
            queryset = get_organization_queryset(
                self.jar_model_uri,
                self.jar_query_uri_code,
                list(selected_choices)[0]
            )
        for obj in queryset:
            option_value = self.choices.choice(obj)[0]
            option_label = self.label_from_instance(obj)

            selected = str(option_value) in value and (
                has_selected is False or self.allow_multiple_selected
            )
            if selected is True and has_selected is False:
                has_selected = True
            index = len(default[1])
            subgroup = default[1]
            subgroup.append(
                self.create_option(
                    name, option_value, option_label, selected_choices, index
                )
            )
        return groups


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
            elif not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
        return name

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.width < 256 or image.height < 256:
                raise ValidationError(_("Nuotraukos dydis turi būti ne mažesnis už 256x256."))
        return image


class OrganizationCreateForm(ModelForm):
    title = CharField(label=_('Pavadinimas'), required=True)
    company_code = CharField(label=_('Registracijos numeris'), required=True)
    name = CharField(label=_('Kodinis pavadinimas'), required=True)
    jurisdiction = ModelChoiceField(queryset=Organization.objects.filter(role__isnull=False),
                                    label=_('Jurisdikcija'),
                                    required=True)
    image = FilerImageField(label=_("Paveiksliukas"), required=False, upload_to=Organization.UPLOAD_TO)
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
        initial = kwargs.get('initial')
        disable_fields = True if initial else False
        button = ("Sukurti")
        parent = self.instance.get_parent()
        if parent:
            self.fields['jurisdiction'].initial = parent
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "organization-form"
        self.helper.layout = Layout(
            Field('title', placeholder=_("Pavadinimas")),
            Field('company_code', placeholder=_("Registracijos numeris")),
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
        if initial:
            self.fields['title'].widget.attrs['readonly'] = True
            self.fields['company_code'].widget.attrs['readonly'] = True
            self.fields['address'].widget.attrs['readonly'] = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            if not name.islower():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti mažoji raidė."))
            elif any((not c.isalnum() and c != '_') for c in name):
                raise ValidationError(_("Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, "
                                        "žodžiai gali būti atskirti _ simboliu,"
                                        "jokie kiti simboliai negalimi."))
            elif not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
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
    regenerate_api_key = BooleanField(label=_("Pergeneruoti raktą"), required=False)
    subscribe = BooleanField(label=_("Prenumeruoti pranešimus"), required=False)

    object_model = Organization

    class Meta:
        model = Representative
        fields = ('role', 'has_api_access', 'regenerate_api_key',)

    def __init__(self, *args, **kwargs):
        self.object = kwargs.pop('object', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Field('role'),
            Field('has_api_access'),
            Field('regenerate_api_key'),
            Field('subscribe'),
            Submit('submit', _("Redaguoti"), css_class='button is-primary'),
        )

        try:
            content_type = ContentType.objects.get_for_model(self.object_model)
            subscription = Subscription.objects.get(user=self.instance.user,
                                                    content_type=content_type,
                                                    object_id=self.object.id)
            if subscription:
                self.fields['subscribe'].initial = True
        except ObjectDoesNotExist:
            self.fields['subscribe'].initial = False

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
    subscribe = BooleanField(label=_("Prenumeruoti pranešimus"), required=False, disabled=True, initial=True)

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
            Field('subscribe'),
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


def get_document_field_title():
    template = Template.objects.filter(identifier=Template.REPRESENTATIVE_REQUEST_ID).first()
    if template:
        return mark_safe(
            f"<span>{_('Prašymas')} *</span>&nbsp;&nbsp;&nbsp;"
            f"<span style='font-size: 0.9rem; font-weight: 500'>"
            f"<a href={template.document.url} download><i class='fa fa-file'></i> {template.text}</a>"
            f"</span>"
        )
    else:
        return _("Prašymas") + " *"


class PartnerRegisterForm(ModelForm):
    organization = ChoiceFieldRequiredValidationOnly(
        label=_("Organizacija"),
        required=True,
        widget=OrganizationWidget(attrs={
            "data-placeholder": "Organizacijos paieška, įveskite simbolį",
            "style": "min-width: 650px;", 'data-width': '100%', 'data-minimum-input-length': 0
        }),
        queryset=Organization.public.all()
    )
    coordinator_phone_number = CharField(label=_("Koordinatoriaus telefono numeris"))
    request_form = TranslatedFileField(
        label=get_document_field_title,
        required=True,
        widget=TranslatedFileInput(file_input_text=_("Pridėti dokumentą"))
    )

    class Meta:
        model = Organization
        fields = [
            'organization',
            'coordinator_phone_number',
            'request_form'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "partner-register-form"
        self.helper.layout = Layout(
            Field('organization'),
            Field('coordinator_phone_number', placeholder=_('Formatas 0... arba +370...')),
            Field('request_form'),
            Submit('submit', _("Sukurti"), css_class='button is-primary')
        )

    def clean_coordinator_phone_number(self):
        phone = self.cleaned_data.get('coordinator_phone_number')
        if phone:
            if (
                not phone.startswith("0") and
                not phone.startswith("+370")
            ):
                raise ValidationError(_("Neteisingas telefono numerio formatas."))
            else:
                if phone.startswith("0"):
                    phone_end = phone.replace("0", "", 1)
                else:
                    phone_end = phone.replace("+370", "", 1)

                if (
                    len(phone_end) != 8 or
                    not all([c in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] for c in phone_end])
                ):
                    raise ValidationError(_("Neteisingas telefono numerio formatas."))
        return phone

    def clean_request_form(self):
        request_form = self.cleaned_data.get('request_form')
        if request_form:
            validate_file(request_form)
        return request_form


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


class ProjectApiKeyForm(ModelForm):
    project_id = IntegerField(widget=HiddenInput(), required=False)

    class Meta:
        model = ApiKey
        fields = ('project_id',)

    def __init__(self, project, *args, **kwargs):
        self.project = project
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "project-apikey-form"
        self.helper.layout = Layout(
            Field('project_id'),
            Submit('submit', _("Sukurti"), css_class='button is-primary'),
        )

        self.initial['project_id'] = self.project.pk


class ApiKeyForm(ModelForm):
    organization_id = IntegerField(widget=HiddenInput(), required=False)
    client_name = CharField(label=_('Pavadinimas'), required=False)

    class Meta:
        model = ApiKey
        fields = ('organization_id', 'client_name',)

    def __init__(self, organization, *args, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "apikey-form"
        self.helper.layout = Layout(
            Field('organization_id'),
            Field('client_name'),
            Submit('submit', _('Redaguoti') if instance else _("Sukurti"), css_class='button is-primary'),
        )

        self.initial['organization_id'] = self.organization.pk

    def clean_client_name(self):
        name = self.cleaned_data.get('client_name')
        if name:
            expr = "^[a-z0-9_]*$"
            found = re.search(expr, name)
            if not found:
                raise ValidationError(_("Pavadinime gali būti mažosios raidės ir skaičiai, "
                                        "žodžiai gali būti atskirti _ simboliu,"
                                        "jokie kiti simboliai negalimi."))
            else:
                return name


class ProjectApiKeyForm(ModelForm):
    project_id = IntegerField(widget=HiddenInput(), required=False)
    client_name = CharField(label=_('Pavadinimas'), required=False)

    class Meta:
        model = ApiKey
        fields = ('project_id', 'client_name',)

    def __init__(self, project, *args, **kwargs):
        self.project = project
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "project-apikey-form"
        self.helper.layout = Layout(
            Field('project_id'),
            Field('client_name'),
            Submit('submit', _('Redaguoti') if instance else _("Sukurti"), css_class='button is-primary'),
        )

        self.initial['project_id'] = self.project.pk

    def clean_client_name(self):
        name = self.cleaned_data.get('client_name')
        if name:
            expr = "^[a-z0-9_]*$"
            found = re.search(expr, name)
            if not found:
                raise ValidationError(_("Pavadinime gali būti mažosios raidės ir skaičiai, "
                                        "žodžiai gali būti atskirti _ simboliu,"
                                        "jokie kiti simboliai negalimi."))
            else:
                return name


class ApiKeyRegenerateForm(ModelForm):
    organization_id = IntegerField(widget=HiddenInput(), required=False)
    new_key = CharField(label=_('Naujas slaptažodis'), required=False, disabled=True,
                        help_text="Naujas raktas parodomas tik vieną kartą, \n"
                                  + "po pakeitimo, nebebus galimybės pamatyti rakto, todėl jis turi būti išsisaugotas!")

    class Meta:
        model = ApiKey
        fields = ('organization_id', 'new_key',)

    def __init__(self, organization, *args, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "apikey-regenerate-form"
        self.helper.layout = Layout(
            Field('organization_id'),
            Field('new_key'),
            Submit('submit', _('Redaguoti') if instance else _("Sukurti"), css_class='button is-primary'),
        )

        api_key = secrets.token_urlsafe()

        self.initial['new_key'] = api_key
        self.initial['organization_id'] = self.organization.pk


class ProjectApiKeyRegenerateForm(ModelForm):
    project_id = IntegerField(widget=HiddenInput(), required=False)
    new_key = CharField(label=_('Naujas slaptažodis'), required=False, disabled=True,
                        help_text="Naujas raktas parodomas tik vieną kartą, \n"
                                  + "po pakeitimo, nebebus galimybės pamatyti rakto, todėl jis turi būti išsisaugotas!")

    class Meta:
        model = ApiKey
        fields = ('project_id', 'new_key',)

    def __init__(self, project, *args, **kwargs):
        self.project = project
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "project-apikey-regenerate-form"
        self.helper.layout = Layout(
            Field('project_id'),
            Field('new_key'),
            Submit('submit', _("Saugoti"), css_class='button is-primary'),
        )

        api_key = secrets.token_urlsafe()

        self.initial['new_key'] = api_key
        self.initial['project_id'] = self.project.pk


class ApiScopeForm(Form):
    scope = CharField(label=_('Objektas'), required=True)
    read = BooleanField(label=_('Skaityti'), widget=CheckboxInput, required=False)
    write = BooleanField(label=_('Rašyti'), widget=CheckboxInput, required=False)
    remove = BooleanField(label=_('Valyti'), widget=CheckboxInput, required=False)

    def __init__(self, organization, api_key, scope, *args, **kwargs):
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]

        self.organization = organization
        self.api_key = api_key
        self.scope = scope
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "apiscope-form"
        self.helper.layout = Layout(
            Field('scope'),
            Field('read'),
            Field('write'),
            Field('remove'),
            Submit('submit', _("Sukurti"), css_class='button is-primary'),
        )
        self.initial['scope'] = self.scope
        if self.scope:
            if scope == '(viskas)':
                scopes = ApiScope.objects.filter(key=api_key).exclude(scope__icontains='datasets_gov')
            else:
                scopes = ApiScope.objects.filter(key=api_key, scope__icontains=self.scope)

            for sc in scopes:
                if any(s in sc.scope for s in read):
                    self.initial['read'] = True
                if any(s in sc.scope for s in write):
                    self.initial['write'] = True
                if 'wipe' in sc.scope:
                    self.initial['remove'] = True

    def clean(self):
        scope = self.cleaned_data.get('scope')
        read = self.cleaned_data.get('read')
        write = self.cleaned_data.get('write')
        remove = self.cleaned_data.get('remove')
        if scope:
            if scope == 'spinta_set_meta_fields' or scope == 'set_meta_fields':
                if read or write or remove:
                    self.add_error('scope', _("Šiai sričiai negalima pridėti skaitymo/rašymo/šalinimo veiksmų."))
            else:
                if scope != '(viskas)':
                    target_org = Organization.objects.filter(name=scope)
                    target_dataset = Metadata.objects.filter(
                        content_type=ContentType.objects.get_for_model(Dataset),
                        name=scope)
                    if not target_org.exists() and not target_dataset.exists():
                        self.add_error('scope', _("Objektas su tokia name reikšme neegzistuoja."))
        return self.cleaned_data


class RepresentativeRequestForm(ModelForm):
    user_name = CharField(label=_("Naudotojas"))
    organization_name = CharField(label=_("Organizacija"))
    phone_number = CharField(label=_("Telefono numeris"))
    document = TranslatedFileField(label=_("Pridėtas dokumentas"))

    class Meta:
        model = RepresentativeRequest
        fields = ('user_name', 'email', 'phone_number', 'organization_name', 'document',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.fields["user_name"].disabled = True
        self.fields["user_name"].widget.attrs['style'] = "background-color: #f2f2f2;"
        self.fields["email"].disabled = True
        self.fields["email"].widget.attrs['style'] = "background-color: #f2f2f2;"
        self.fields["phone_number"].disabled = True
        self.fields["phone_number"].widget.attrs['style'] = "background-color: #f2f2f2;"
        self.fields["organization_name"].disabled = True
        self.fields["organization_name"].widget.attrs['style'] = "background-color: #f2f2f2;"

        if instance:
            self.initial['user_name'] = str(instance.user)
            self.initial['organization_name'] = str(instance.organization)
            if instance.phone:
                self.initial['phone_number'] = instance.phone
            else:
                self.initial['phone_number'] = '-'


class TemplateForm(ModelForm):
    document = TranslatedFileField(label=_("Pridėtas dokumentas"))

    class Meta:
        model = Template
        fields = ('text', 'document',)

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            validate_file(document)
        return document
