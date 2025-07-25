from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models.fields.files import FieldFile
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.models import Organization
from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.models import AgreementFile
from vitrina.smart_contracts.services import has_valid_signature
from vitrina.structure.models import Metadata


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
        dataset_metadata_by_organization = kwargs.pop(
            "dataset_metadata_by_organization", {}
        )
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields["scopes"].choices = self.create_scope_choices(
            dataset_metadata_by_organization.get(self.instance.id, [])
        )

    @staticmethod
    def create_scope_choices(dataset_metadata: list[Metadata]) -> list[tuple[str, str]]:
        choices = []
        for metadata in dataset_metadata:
            if not metadata.name:
                continue

            choice_name = metadata.name.replace("/", "_")
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


class AgreementUploadForm(forms.ModelForm):
    class Meta:
        model = AgreementFile
        fields = ("file",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].validators = [
            FileExtensionValidator(
                allowed_extensions=["adoc"],
                message=_("Dokumentas turi būti adoc formato."),
            )
        ]
        self.helper = FormHelper()
        self.helper.form_id = "agreement-upload-form"
        self.helper.add_input(
            Submit("submit", _("Įkelti dokumentą"), css_class="button is-primary")
        )

    def clean_file(self) -> FieldFile:
        file = self.cleaned_data["file"]
        try:
            # TODO: check for multiple signatures if AgreementStatuses.INITIATED
            # TODO: check agreement checksum
            # TODO: https://github.com/atviriduomenys/katalogas/issues/1706
            signature_valid = has_valid_signature(file)
        except InvalidAdocError as error:
            raise ValidationError(str(error))

        if not signature_valid:
            raise ValidationError(_("Įkelta sutartis nepasirašyta."))

        return file
