from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, Submit
from django.forms import ModelForm, CharField, ImageField, Textarea

from vitrina.projects.models import Project

from django.utils.translation import gettext_lazy as _


class ProjectForm(ModelForm):
    title = CharField(label=_('Pavadinimas'))
    description = CharField(label=_('Aprašymas'), widget=Textarea)
    url = CharField(label="Nuoroda į panaudojimo atvejį", required=False)
    image = ImageField(label=_("Paveiksliukas"))

    class Meta:
        model = Project
        fields = ['title', 'description', 'url', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = "Update" if project_instance else "Create"
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(Field('title', css_class="input", placeholder=_("Pavadinimas"),),
                    css_class="control"), css_class="field"),
            Div(Div(Field('description', css_class="textarea", placeholder=_("Aprašymas")),
                    css_class="control"), css_class="field"),
            Div(Div(Field('url', css_class="input", placeholder="Nuoroda į panaudojimo atvejį"),
                    css_class="control"), css_class="field"),
            Div(Div(Field('image'), css_class="control"), css_class="field"),
            Submit('submit', button, css_class='button is-primary')
        )
