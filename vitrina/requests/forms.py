from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from django.forms import ModelForm, DateField, CharField, Textarea
from haystack.forms import FacetedSearchForm
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
        self.helper.form_id = "request-form"
        self.helper.layout = Layout(
            Field('title', placeholder=_('Pavadinimas')),
            Field('description', placeholder=_('Aprašymas')),
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
        if self.cleaned_data.get('date_from'):
            sqs = sqs.filter(created__gte=self.cleaned_data['date_from'])
        if self.cleaned_data.get('date_to'):
            sqs = sqs.filter(created__lte=self.cleaned_data['date_to'])
        return sqs

    def no_query_found(self):
        return self.searchqueryset.all()