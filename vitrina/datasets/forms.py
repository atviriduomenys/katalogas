from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Value, CharField as _CharField, Case, When
from django.db.models.functions import Concat
from django.utils.safestring import mark_safe
from django_select2.forms import ModelSelect2Widget
from parler.forms import TranslatableModelForm, TranslatedField
from parler.views import TranslatableModelFormMixin
from django import forms
from django.forms import TextInput, CharField, DateField, ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout
from haystack.forms import FacetedSearchForm
from treebeard.forms import MoveNodeForm

from vitrina.datasets.services import get_projects
from vitrina.classifiers.models import Frequency, Licence, Category
from vitrina.fields import FilerFileField
from vitrina.helpers import get_current_domain
from vitrina.orgs.forms import RepresentativeCreateForm, RepresentativeUpdateForm

from vitrina.datasets.models import Dataset, DatasetStructure, DatasetGroup, Type, DatasetRelation, Relation


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
    groups = forms.ModelMultipleChoiceField(
        label=_('Grupės'),
        queryset=DatasetGroup.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
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

    class Meta:
        model = Dataset
        fields = (
            'is_public',
            'tags',
            'category',
            'licence',
            'frequency',
            'access_rights',
            'distribution_conditions',
            'type',
            'endpoint_url',
            'endpoint_type',
            'endpoint_description',
            'endpoint_description_type',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if project_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.form_id = "dataset-form"
        self.helper.layout = Layout(
            Field('is_public',
                  placeholder=_('Ar duomenys vieši')),
            Field('title',
                  placeholder=_('Duomenų rinkinio pavadinimas')),
            Field('description',
                  placeholder=_('Detalus duomenų rinkinio aprašas')),
            Field('tags',
                  placeholder=_('Surašykite aktualius raktinius žodžius')),
            Field('groups'),
            Field('category'),
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

        category_choices = MoveNodeForm.mk_dropdown_tree(Category)
        category_choices[0] = (None, "---------")
        self.fields['category'].choices = category_choices

        if not project_instance:
            if Licence.objects.filter(is_default=True).exists():
                default_licence = Licence.objects.filter(is_default=True).first()
                self.initial['licence'] = default_licence
            if Frequency.objects.filter(is_default=True).exists():
                default_frequency = Frequency.objects.filter(is_default=True).first()
                self.initial['frequency'] = default_frequency
        else:
            groups = DatasetGroup.objects.filter(dataset=project_instance).all()
            if len(groups) > 0:
                self.initial['groups'] = groups

    def clean_type(self):
        type = self.cleaned_data.get('type')
        if (
            type.filter(name=Type.SERVICE).exists() and
            type.filter(name=Type.SERIES).exists()
        ):
            raise ValidationError(_('Tipai "service" ir "series" negali būti pažymėti abu kartu, '
                                    'gali būti pažymėtas tik vienas arba kitas.'))
        return type


class DatasetSearchForm(FacetedSearchForm):
    date_from = DateField(required=False)
    date_to = DateField(required=False)

    def search(self):
        sqs = super().search()

        if not self.is_valid():
            return self.no_query_found()
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
        self.helper.form_id = "dataset-structure-form"
        self.helper.layout = Layout(
            Field('file'),
            Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )


class AddProjectForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['projects']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.dataset = kwargs.pop('dataset', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
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


class DatasetMemberUpdateForm(RepresentativeUpdateForm):
    object_model = Dataset


class DatasetMemberCreateForm(RepresentativeCreateForm):
    object_model = Dataset


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
