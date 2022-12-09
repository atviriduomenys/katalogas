from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.forms import ModelForm, CharField, Textarea

from vitrina.fields import FilerImageField
from vitrina.projects.models import Project

from django.utils.translation import gettext_lazy as _


class ProjectForm(ModelForm):
    title = CharField(label=_('Pavadinimas'))
    description = CharField(label=_('Aprašymas'), widget=Textarea)
    url = CharField(label=_("Nuoroda į panaudojimo atvejį"), required=False)
    image = FilerImageField(label=_("Paveiksliukas"), required=False, upload_to=Project.UPLOAD_TO)

    class Meta:
        model = Project
        fields = ['title', 'description', 'url', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if project_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.form_id = "project-form"
        self.helper.layout = Layout(
            Field('title', placeholder=_("Pavadinimas")),
            Field('description', placeholder=_("Aprašymas")),
            Field('url', placeholder=_("Nuoroda į panaudojimo atvejį")),
            Field('image'),
            Submit('submit', button, css_class='button is-primary')
        )
