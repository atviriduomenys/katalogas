from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout, HTML

from vitrina.api_example.models import ApiExample


class YamlFileUploadForm(forms.ModelForm):
    class Meta:
        model = ApiExample
        fields = ["yaml_file"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "file_upload_form"
        self.helper.layout = Layout(
            Field("yaml_file"),
            Submit("submit", _("Patvirtinti"), css_class="button is-primary"),
        )
