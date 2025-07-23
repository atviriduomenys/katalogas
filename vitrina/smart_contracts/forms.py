from crispy_forms.helper import FormHelper
from django import forms
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization


class SmartContractForm(forms.ModelForm):
    scopes = forms.MultipleChoiceField(
        label=_("Leidimai"),
        choices=(),
        required=False,
        widget=CheckboxSelectMultiple,
    )

    class Meta:
        model = Organization
        fields = ("scopes",)

    def __init__(self, *args, **kwargs) -> None:
        datasets_by_organization = kwargs.pop("datasets_by_organization", {})
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields["scopes"].choices = self.create_scope_choices(
            datasets_by_organization.get(self.instance, [])
        )

    @staticmethod
    def create_scope_choices(datasets: list[Dataset]) -> list[tuple[str, str]]:
        choices = []
        for dataset in datasets:
            if (dataset_metadata := dataset.metadata.first()) and dataset_metadata.name:
                choice_name = dataset_metadata.name.replace("/", "_")
                choices.extend(
                    [
                        (f"{choice_name}_getall", f"{choice_name}_getall"),
                        (f"{choice_name}_search", f"{choice_name}_search"),
                        (f"{choice_name}_select", f"{choice_name}_select"),
                    ]
                )

        return choices


class SmartContractFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False
