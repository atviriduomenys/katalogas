import yaml

from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout

from vitrina.api_example.models import ApiExample


class YamlFileUploadForm(forms.ModelForm):
    code_field = forms.CharField(
        widget=forms.Textarea(attrs={"class": "codemirror"}),
        label="Duomenys YAML formatu:",
    )

    class Meta:
        model = ApiExample
        fields = ["code_field"]

    def __init__(self, *args, **kwargs):
        self.dataset = kwargs.pop("dataset", None)
        super().__init__(*args, **kwargs)
        yaml_content = ""
        if self.dataset:
            example = ApiExample.objects.filter(dataset=self.dataset).first()
            if example and example.yaml_file:
                with example.yaml_file.open() as file:
                    yaml_content = file.read().decode("utf-8").strip()
                    yaml_content = yaml.dump(
                        yaml.safe_load(yaml_content),
                        default_flow_style=False,
                        allow_unicode=True,
                    )

        self.initial["code_field"] = yaml_content
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "file_upload_form"
        self.helper.layout = Layout(
            Field("code_field"),
            Submit("submit", _("Patvirtinti"), css_class="button is-primary"),
        )
