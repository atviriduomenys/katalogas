from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from django.forms import ModelForm, CharField, Textarea

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
        button = "Update" if request_instance else "Create"
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(Field('title', css_class='input', placeholder='Title'), css_class='control'), css_class='field'),
            Div(Div(Field('description', css_class='textarea', placeholder='Description'), css_class='control'),
                css_class='field'),
            Submit('submit', button, css_class='button is-primary')
        )
