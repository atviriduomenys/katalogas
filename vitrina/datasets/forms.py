from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db.models import Value, CharField as _CharField, Case, When, Count, Q
from django.db.models.functions import Concat
from django.utils.safestring import mark_safe
from django_select2.forms import ModelSelect2Widget
from parler.forms import TranslatableModelForm, TranslatedField
from parler.views import TranslatableModelFormMixin
from django import forms
from django.forms import TextInput, CharField, DateField, ModelMultipleChoiceField, Form, ModelChoiceField, \
    CheckboxSelectMultiple, HiddenInput
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout, HTML
from haystack.forms import FacetedSearchForm
from treebeard.forms import MoveNodeForm

from vitrina.datasets.services import get_projects, get_requests
from vitrina.classifiers.models import Frequency, Licence, Category
from vitrina.fields import FilerFileField, MultipleFilerField
from vitrina.helpers import get_current_domain
from vitrina.orgs.forms import RepresentativeCreateForm, RepresentativeUpdateForm, OrganizationPlanForm

from vitrina.datasets.models import Dataset, DatasetStructure, DatasetGroup, DatasetAttribution, Type, DatasetRelation, Relation
from vitrina.orgs.models import Organization
from vitrina.plans.models import PlanDataset, Plan
from vitrina.structure.models import Metadata


class DatasetTypeField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if obj.description:
            return mark_safe(f'{obj.title}<br/><p class="help">{obj.description}</p>')
        else:
            return obj.title


class DatasetForm(TranslatableModelForm, TranslatableModelFormMixin):
    title = TranslatedField(form_class=CharField, label=_('Pavadinimas'), required=True, widget=TextInput())
    type = DatasetTypeField(
        label=_("Duomenų rinkinio tipas"),
        required=False,
        queryset=Type.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )
    description = TranslatedField(label=_('Aprašymas'))
    endpoint_url = forms.CharField(
        label=_("API adresas"),
        required=False,
        help_text=_("Pagrindinis API paslaugos adresas")
    )
    endpoint_description = forms.CharField(
        label=_("API specifikacija"),
        required=False,
        help_text=_(
            "Nuoroda į API specifikaciją, pavyzdžiui OpenAPI (Swagger), WSDL ar kitas API "
            "specifikacijos formatas, gali būti ir nuoroda į API dokumentaciją, kuri nėra "
            "nuskaitoma mašininiu būdu"
        )
    )
    files = MultipleFilerField(label=_("Failai"), required=False, upload_to=Dataset.UPLOAD_TO)
    name = forms.CharField(label=_("Kodinis pavadinimas"), required=False, validators=[
            RegexValidator(
                '([a-z]+\/?)+',
                message="Kodinis pavadinimas turi būti sudarytas iš mažųjų raidžių ir (arba) gali turėti pasvirųjų brūkšnių"
            )
        ])

    class Meta:
        model = Dataset
        fields = (
            'is_public',
            'tags',
            'catalog',
            'licence',
            'frequency',
            'access_rights',
            'distribution_conditions',
            'type',
            'endpoint_url',
            'endpoint_type',
            'endpoint_description',
            'endpoint_description_type',
            'files',
            'name',
        )
        labels = {
            'tags': _("Žymės"),
            'catalog': _("Katalogas")
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "dataset-form"
        self.helper.layout = Layout(
            Field('is_public',
                  placeholder=_('Ar duomenys vieši')),
            Field('title',
                  placeholder=_('Duomenų rinkinio pavadinimas')),
            Field('name',
                  placeholder=_('Duomenų rinkinio kodinis pavadinimas')),
            Field('description',
                  placeholder=_('Detalus duomenų rinkinio aprašas')),
            Field('files'),
            Field('tags',
                  placeholder=_('Surašykite aktualius raktinius žodžius')),
            Field('catalog'),
            Field('licence'),
            Field('frequency'),
            Field('type'),
            Field('endpoint_url'),
            Field('endpoint_type'),
            Field('endpoint_description'),
            Field('endpoint_description_type'),
            Field('access_rights',
                  placeholder=_('Pateikite visas prieigos teises kurios aktualios šiam duomenų rinkiniui')),
            Field('distribution_conditions',
                  placeholder=_('Pateikite visas salygas kurios reikalingos norint platinti duomenų rinkinį')),
            Submit('submit', button, css_class='button is-primary')
        )

        if not instance:
            if Licence.objects.filter(is_default=True).exists():
                default_licence = Licence.objects.filter(is_default=True).first()
                self.initial['licence'] = default_licence
            if Frequency.objects.filter(is_default=True).exists():
                default_frequency = Frequency.objects.filter(is_default=True).first()
                self.initial['frequency'] = default_frequency
        else:
            self.initial['files'] = list(instance.dataset_files.values_list('file', flat=True))
            if instance.name:
                self.initial['name'] = instance.name

    def clean_type(self):
        type = self.cleaned_data.get('type')
        if (
            type.filter(name=Type.SERVICE).exists() and
            type.filter(name=Type.SERIES).exists()
        ):
            raise ValidationError(_('Tipai "service" ir "series" negali būti pažymėti abu kartu, '
                                    'gali būti pažymėtas tik vienas arba kitas.'))
        return type

    def clean_name(self):
        name = self.cleaned_data.get('name')

        if name:
            if self.instance and self.instance.pk and self.instance.metadata.first():
                metadata = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Dataset),
                    name=name
                ).exclude(pk=self.instance.metadata.first().pk)
            else:
                metadata = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Dataset),
                    name=name
                )
            if metadata:
                raise ValidationError(_("Duomenų rinkinys su šiuo kodiniu pavadinimu jau egzistuoja."))

            if not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
            if any([ch.isupper() for ch in name]):
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik mažosios raidės."))
        return name


class DatasetSearchForm(FacetedSearchForm):
    date_from = DateField(required=False)
    date_to = DateField(required=False)

    def search(self):
        sqs = super().search()
        sqs = sqs.models(Dataset)
        if not self.is_valid():
            return self.no_query_found()
        if self.cleaned_data.get('q'):
            keyword = self.cleaned_data.get('q')
            if len(keyword) < 5:
                sqs = sqs.autocomplete(text__startswith=keyword)
            else:
                sqs = sqs.autocomplete(text__icontains=keyword)

            dataset_with_name_ids = self.searchqueryset.models(Dataset).filter(name__icontains=keyword) \
                .values_list('pk', flat=True)
            dataset_with_model_name_ids = self.searchqueryset.models(Dataset).filter(model_names__icontains=keyword) \
                .values_list('pk', flat=True)
            sqs_ids = sqs.values_list('pk', flat=True)
            ids = list(dataset_with_model_name_ids) + list(dataset_with_name_ids) + list(sqs_ids)

            sqs = self.searchqueryset.models(Dataset).filter(id__in=ids)

        if self.cleaned_data.get('date_from'):
            sqs = sqs.filter(published__gte=self.cleaned_data['date_from'])
        if self.cleaned_data.get('date_to'):
            sqs = sqs.filter(published__lte=self.cleaned_data['date_to'])
        return sqs

    def no_query_found(self):
        return self.searchqueryset.all()


class DatasetStructureImportForm(forms.ModelForm):
    file = FilerFileField(label=_("Failas"), required=True, upload_to=DatasetStructure.UPLOAD_TO)

    class Meta:
        model = DatasetStructure
        fields = ('file',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "dataset-structure-form"
        self.helper.layout = Layout(
            Field('file'),
            Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )


class OrganizationWidget(ModelSelect2Widget):
    model = Organization
    search_fields = ['title__icontains']
    max_results = 10

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)
        queryset = queryset.annotate(
            attribution_count=Count('datasetattribution')
        ).order_by('-attribution_count')
        return queryset


class DatasetAttributionForm(forms.ModelForm):
    organization = forms.ModelChoiceField(
        label=_("Organizacija"),
        required=False,
        queryset=Organization.public.all(),
        widget=OrganizationWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0})
    )

    class Meta:
        model = DatasetAttribution
        fields = ('attribution', 'organization', 'agent',)

    def __init__(self, dataset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = dataset

        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "attribution-form"
        self.helper.layout = Layout(
            Field('attribution'),
            Field('organization'),
            Field('agent'),
            Submit('submit', _('Sukurti'), css_class='button is-primary'),
        )

    def clean(self):
        attribution = self.cleaned_data.get('attribution')
        organization = self.cleaned_data.get('organization')
        agent = self.cleaned_data.get('agent')

        if organization and agent:
            self.add_error('organization', _('Negalima užpildyti abiejų "Organizacija" ir "Agentas" laukų.'))

        elif not organization and not agent:
            self.add_error('organization', _('Privaloma užpildyti "Organizacija" arba "Agentas" lauką.'))

        elif organization and DatasetAttribution.objects.filter(
            dataset=self.dataset,
            organization=organization,
            attribution=attribution,
        ).exists():
            self.add_error('organization', _(f'Ryšys "{attribution}" su šia organizacija jau egzistuoja.'))

        elif agent and DatasetAttribution.objects.filter(
            dataset=self.dataset,
            agent=agent,
            attribution=attribution,
        ).exists():
            self.add_error('agent', _(f'Ryšys "{attribution}" su šiuo agentu jau egzistuoja.'))

        return self.cleaned_data


class AddProjectForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['projects']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.dataset = kwargs.pop('dataset', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "dataset-add-project-form"
        self.fields['projects'].queryset = get_projects(self.user, self.dataset, form_query=True)
        self.helper.layout = Layout(
            Field('projects'),
            Submit('submit', _("Pridėti"), css_class='button is-primary')
        )

    projects = ModelMultipleChoiceField(
        label=_('Projektai'),
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text=_(
            "Pažymėkite projektus, kuriuose yra naudojamas šis duomenų "
            "rinkinys."
        ),
    )


class AddRequestForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['requests']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.dataset = kwargs.pop('dataset', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "dataset-add-request-form"
        self.fields['requests'].queryset = get_requests(self.user, self.dataset)
        self.helper.layout = Layout(
            Field('requests'),
            Submit('submit', _("Pridėti"), css_class='button is-primary')
        )

    requests = ModelMultipleChoiceField(
        label=_('Poreikiai'),
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text=_(
            "Pažymėkite poreikius, kuriuose yra naudojamas šis duomenų "
            "rinkinys."
        ),
    )


class DatasetMemberUpdateForm(RepresentativeUpdateForm):
    object_model = Dataset


class DatasetMemberCreateForm(RepresentativeCreateForm):
    object_model = Dataset


class DatasetCategoryForm(Form):
    search = CharField(label=_("Paieška"), required=False)
    group = ModelChoiceField(label=_("Grupė"), required=False, queryset=DatasetGroup.objects.all())
    category = ModelMultipleChoiceField(
        label=_("Kategorija"),
        required=False,
        queryset=Category.objects.all(),
        widget=CheckboxSelectMultiple
    )

    def __init__(self, dataset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = dataset

        self.helper = FormHelper()
        self.helper.form_id = "dataset-category-form"
        self.helper.layout = Layout(
            Field('group'),
            Field('search'),
            HTML(f'<div class="mt-4 mb-3"><input type="checkbox" id="show_selected_id"/>'
                 f'<strong>{_("Rodyti pasirinktas kategorijas")}</strong></div>'),
            Field('category'),
            Submit('submit', _("Išsaugoti"), css_class='button is-primary')
        )

        category_choices = MoveNodeForm.mk_dropdown_tree(Category)
        category_choices = category_choices[1:]
        self.fields['category'].choices = category_choices
        self.initial['category'] = self.dataset.category.all()


class PartOfWidget(ModelSelect2Widget):
    model = Dataset
    search_fields = [
        'translations__title__icontains',
        'absolute_url__icontains']
    dependent_fields = {'organization_id': 'organization__pk'}
    max_results = 10

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        organization_id = None
        if 'organization__pk' in dependent_fields:
            organization_id = dependent_fields.pop('organization__pk')
        if queryset:
            domain = get_current_domain(request)
            queryset = queryset.annotate(
                absolute_url=Concat(Value(domain), Value('/datasets/'), 'pk', Value('/'), output_field=_CharField())
            )
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)
        if organization_id:
            organization_datasets = queryset.filter(organization__pk=organization_id).values_list('pk', flat=True)
            if organization_datasets:
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(organization_datasets)])
                queryset = queryset.order_by(preserved)
        return queryset


class DatasetRelationForm(forms.ModelForm):
    organization_id = forms.IntegerField(widget=forms.HiddenInput)
    part_of = forms.ModelChoiceField(
        label=_("Duomenų rinkinys"),
        widget=PartOfWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0}),
        queryset=Dataset.public.all()
    )
    relation_type = forms.ChoiceField(label=_("Ryšio tipas"))

    class Meta:
        model = DatasetRelation
        fields = ('organization_id', 'relation_type', 'part_of',)

    def __init__(self, dataset, *args, **kwargs):
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "dataset-relation-form"
        self.helper.layout = Layout(
            Field('organization_id'),
            Field('relation_type'),
            Field('part_of'),
            Submit('submit', _("Pridėti"), css_class='button is-primary')
        )

        self.initial['organization_id'] = self.dataset.organization.pk

        relation_choices = [(None, '---------')]
        for rel in Relation.objects.all():
            relation_choices.append((f"{rel.pk}", rel.title))
            relation_choices.append((f'{rel.pk}_inv', rel.inversive_title))
        self.fields['relation_type'].choices = tuple(relation_choices)

    def clean_part_of(self):
        part_of = self.cleaned_data.get('part_of')
        relation = self.cleaned_data.get('relation_type')

        if relation:
            inverse = False
            if relation.endswith('_inv'):
                relation = relation.replace('_inv', '')
                inverse = True
            try:
                relation = Relation.objects.get(pk=int(relation))
            except (ValueError, ObjectDoesNotExist):
                raise ValidationError(_("Neteisinga ryšio tipo reikšmė."))

            if inverse:
                if DatasetRelation.objects.filter(
                    relation=relation,
                    dataset=part_of,
                    part_of=self.dataset
                ):
                    raise ValidationError(_(f'"{relation.inversive_title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.'))
            else:
                if DatasetRelation.objects.filter(
                    relation=relation,
                    dataset=self.dataset,
                    part_of=part_of
                ):
                    raise ValidationError(_(f'"{relation.title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.'))

        return part_of


class PlanChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.deadline:
            return mark_safe(f"<a href={obj.get_absolute_url()}>{obj.title} ({obj.deadline})</a>")
        else:
            return mark_safe(f"<a href={obj.get_absolute_url()}>{obj.title}</a>")


class DatasetPlanForm(forms.ModelForm):
    plan = PlanChoiceField(
        label=_("Terminas"),
        widget=forms.RadioSelect(),
        queryset=Plan.objects.all()
    )
    form_type = CharField(widget=HiddenInput(), initial="include_form")

    class Meta:
        model = PlanDataset
        fields = ('plan', 'form_type',)

    def __init__(self, dataset, *args, **kwargs):
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "dataset-plan-form"
        self.helper.layout = Layout(
            Field('form_type'),
            Field('plan'),
            Submit('submit', _('Įtraukti'), css_class='button is-primary'),
        )

        self.fields['plan'].queryset = self.fields['plan'].queryset.filter(
            Q(deadline__isnull=True) |
            Q(deadline__gt=date.today())
        )

    def clean_plan(self):
        plan = self.cleaned_data.get('plan')
        if PlanDataset.objects.filter(
            plan=plan,
            dataset=self.dataset
        ):
            raise ValidationError(_("Duomenų rinkinys jau priskirtas šiam planui."))
        return plan


class PlanForm(OrganizationPlanForm):
    form_type = CharField(widget=HiddenInput(), initial="create_form")

    class Meta:
        model = Plan
        fields = ('title', 'description', 'deadline', 'provider', 'provider_title', 'receiver',)

    def __init__(self, obj, organizations, user, *args, **kwargs):
        self.obj = obj
        super().__init__(organizations, user, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "plan-form"
        self.helper.layout = Layout(
            Field('form_type'),
            Field('organizations'),
            Field('user_id'),
            Field('title'),
            Field('description'),
            Field('deadline'),
            Field('receiver'),
            Field('provider'),
            Field('provider_title'),
            Submit('submit', _('Įtraukti'), css_class='button is-primary'),
        )

        if len(self.organizations) == 1:
            self.initial['receiver'] = self.organizations[0]
            self.fields['receiver'].widget = HiddenInput()
        else:
            organization_ids = [org.pk for org in self.organizations]
            self.fields['receiver'].queryset = self.fields['receiver'].queryset.filter(pk__in=organization_ids)

        self.initial['title'] = self.obj.get_plan_title()
