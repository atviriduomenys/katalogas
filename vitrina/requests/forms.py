from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from haystack.forms import FacetedSearchForm, SearchForm
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm, CharField, ModelMultipleChoiceField, MultipleChoiceField, CheckboxSelectMultiple, \
    Textarea, ModelChoiceField, RadioSelect, DateField, HiddenInput
from django.utils.safestring import mark_safe
from django_select2.forms import ModelSelect2MultipleWidget
from vitrina.requests.search_indexes import RequestIndex

from vitrina.plans.models import PlanRequest, Plan
from vitrina.requests.models import Request
from vitrina.orgs.models import Organization

from django.utils.translation import gettext_lazy as _
from functools import reduce
from vitrina.orgs.search_indexes import OrganizationIndex
from django.db.models import Count



class ProviderWidget(ModelSelect2MultipleWidget, SearchForm):
    empty_label = "Pasirinkite organizacijas"
    search_fields = ("title__icontains",)
    is_bound = False

    def build_attrs(self, base_attrs, extra_attrs=None):
        base_attrs = super().build_attrs(base_attrs, extra_attrs)
        base_attrs.update(
            {"data-minimum-input-length": 0, "data-placeholder": "Organizacijų sąrašas ribojamas, įveskite 3 simbolius, kad matytumet daugiau rezultatų", "style": "min-width: 650px;"}
        )
        return base_attrs

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        if queryset is None:
            queryset = self.get_queryset()
        search_fields = self.get_search_fields()
        select = Q()
        term = term.replace("\t", " ")
        term = term.replace("\n", " ")
        for t in [t for t in term.split(" ") if not t == ""]:
            select &= reduce(
                lambda x, y: x | Q(**{y: t}),
                search_fields[1:],
                Q(**{search_fields[0]: t}),
            )
        if dependent_fields:
            select &= Q(**dependent_fields)
        if len(term) > 2:
            return queryset.filter(select).distinct().order_by('title')[:10]
        else:
            return queryset.distinct().annotate(dataset_count=Count('dataset')).order_by('-dataset_count')[:10]

class RequestForm(ModelForm):
    title = CharField(label=_("Pavadinimas"))
    description = CharField(label=_("Aprašymas"), widget=Textarea)
    organizations = ModelMultipleChoiceField(
        label="Organizacija",
        widget=ProviderWidget,
        queryset=Organization.objects.filter(),
        to_field_name="pk",
        required=False
    )

    class Meta:
        model = Request
        fields = ['title', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if request_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "request-form"
        if request_instance:
            self.helper.layout = Layout(
                Field('title', placeholder=_('Pavadinimas')),
                Field('description', placeholder=_('Aprašymas')),
                Submit('submit', button, css_class='button is-primary')
            )
        else:
            self.helper.layout = Layout(
                Field('title', placeholder=_('Pavadinimas')),
                Field('description', placeholder=_('Aprašymas')),
                Field('organizations', placeholder=_('Organizacijos'), id="organization_select_field"),
                Submit('submit', button, css_class='button is-primary')
            )



class RequestEditOrgForm(ModelForm):
    organizations = ModelMultipleChoiceField(
        label="Organizacija",
        widget=ProviderWidget,
        queryset=Organization.objects.filter(),
        to_field_name="pk"
    )

    class Meta:
        model = Request
        fields = ['organizations']

    def __init__(self, *args, initial={}, **kwargs):
        super().__init__(*args, **kwargs)
        button = _("Pridėti")
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "request-add-org-form"
        self.helper.layout = Layout(
            Field('organizations', placeholder=_('Organizacijos')),
            Submit('submit', button, css_class='button is-primary')
        )


class RequestSearchForm(FacetedSearchForm):
    date_from = DateField(required=False)
    date_to = DateField(required=False)

    def search(self):
        sqs = super().search()
        sqs = sqs.models(Request)
        if not self.is_valid():
            return self.no_query_found()
        if self.cleaned_data.get('q'):
             keyword = self.cleaned_data.get('q')
             if len(keyword) < 5:
                q = self.searchqueryset.autocomplete(text__startswith = self.cleaned_data['q'])
             else:
                q = self.searchqueryset.autocomplete(text__contains = self.cleaned_data['q'])
             if len(q) != 0: 
                 sqs = q
        if self.cleaned_data.get('date_from'):
            sqs = sqs.filter(created__gte=self.cleaned_data['date_from'])
        if self.cleaned_data.get('date_to'):
            sqs = sqs.filter(created__lte=self.cleaned_data['date_to'])
        return sqs

    def no_query_found(self):
        return self.searchqueryset.all()


class PlanChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.deadline:
            return mark_safe(f"<a href={obj.get_absolute_url()}>{obj.title} ({obj.deadline})</a>")
        else:
            return mark_safe(f"<a href={obj.get_absolute_url()}>{obj.title}</a>")


class RequestPlanForm(ModelForm):
    plan = PlanChoiceField(
        label=_("Terminas"),
        widget=RadioSelect(),
        queryset=Plan.objects.all()
    )
    form_type = CharField(widget=HiddenInput(), initial="include_form")

    class Meta:
        model = PlanRequest
        fields = ('plan',)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "request-plan-form"
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
        if PlanRequest.objects.filter(
            plan=plan,
            request=self.request
        ):
            raise ValidationError(_("Poreikis jau priskirtas šiam planui."))
        return plan
