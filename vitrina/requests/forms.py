from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from django.core.exceptions import ValidationError
from django.forms import ModelForm, CharField, Textarea, ModelChoiceField, RadioSelect
from django.utils.safestring import mark_safe

from vitrina.plans.models import PlanRequest, Plan
from vitrina.requests.models import Request

from django.utils.translation import gettext_lazy as _


class RequestForm(ModelForm):
    title = CharField(label=_("Pavadinimas"))
    description = CharField(label=_("Aprašymas"), widget=Textarea)

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
        self.helper.layout = Layout(
            Field('title', placeholder=_('Pavadinimas')),
            Field('description', placeholder=_('Aprašymas')),
            Submit('submit', button, css_class='button is-primary')
        )


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

        self.fields['plan'].queryset = self.fields['plan'].queryset.filter(deadline__gt=date.today())

    def clean_plan(self):
        plan = self.cleaned_data.get('plan')
        if PlanRequest.objects.filter(
            plan=plan,
            request=self.request
        ):
            raise ValidationError(_("Poreikis jau priskirtas šiam planui."))
        return plan
