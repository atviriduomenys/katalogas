from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from haystack.forms import FacetedSearchForm
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm, CharField, ModelMultipleChoiceField, MultipleChoiceField, CheckboxSelectMultiple, Textarea, ModelChoiceField, RadioSelect, DateField
from django.utils.safestring import mark_safe
from django_select2.forms import Select2MultipleWidget


from vitrina.plans.models import PlanRequest, Plan
from vitrina.requests.models import Request
from vitrina.orgs.models import Organization

from django.utils.translation import gettext_lazy as _


class ProviderWidget(Select2MultipleWidget):
    empty_label = "Pasirinkite organizacijas"
    search_fields = ("title__icontains",)
    queryset = Organization.objects.order_by('created')

    def build_attrs(self, base_attrs, extra_attrs=None):
        base_attrs = super().build_attrs(base_attrs, extra_attrs)
        base_attrs.update(
            {"data-minimum-input-length": 0, "data-placeholder": self.empty_label}
        )
        return base_attrs



class RequestForm(ModelForm):
    title = CharField(label=_("Pavadinimas"))
    description = CharField(label=_("Aprašymas"), widget=Textarea)
    organizations = ModelMultipleChoiceField(
        label="Organizacija",
        widget=ProviderWidget,
        queryset=ProviderWidget.queryset,
        to_field_name="pk"
    )

    class Meta:
        model = Request
        fields = ['title', 'description', 'organizations']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if request_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "request-form"
        if (kwargs and kwargs.get('data') and kwargs.get('data').get('title') and kwargs.get('data').get('description')):
            self.helper.layout = Layout(
                Field('title', placeholder=_('Pavadinimas'), readonly=True),
                Field('description', placeholder=_('Aprašymas'), readonly=True),
                Field('organizations', placeholder=_('Organizacijos')),
                Submit('submit', button, css_class='button is-primary')
            )
            button = _("Redaguoti") if request_instance else _("Sukurti")
        else:
            self.helper.layout = Layout(
                Field('title', placeholder=_('Pavadinimas')),
                Field('description', placeholder=_('Aprašymas')),
                Submit('submit', button, css_class='button is-primary')
            )
            button = _("Tęsti")


class RequestSearchForm(FacetedSearchForm):
    date_from = DateField(required=False)
    date_to = DateField(required=False)

    def search(self):
        sqs = super().search()
        sqs = sqs.models(Request)
        if not self.is_valid():
            return self.no_query_found()
        if self.cleaned_data.get('date_from'):
            sqs = sqs.filter(created__gte=self.cleaned_data['date_from'])
        if self.cleaned_data.get('date_to'):
            sqs = sqs.filter(created__lte=self.cleaned_data['date_to'])
        return sqs

    def no_query_found(self):
        return self.searchqueryset.all()


class PlanChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return mark_safe(f"<a href={obj.get_absolute_url()}>{obj.title}</a>")


class RequestPlanForm(ModelForm):
    plan = PlanChoiceField(
        label=_("Planas"),
        widget=RadioSelect(),
        queryset=Plan.objects.all()
    )

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
