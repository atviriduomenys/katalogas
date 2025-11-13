from functools import cached_property

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Q, QuerySet
from django.db.models.fields.files import FieldFile
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Contact
from vitrina.orgs.models import Organization
from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.models import (
    AgreementFile,
    SmartContractTemplate,
    Agreement,
)
from vitrina.smart_contracts.services import has_valid_signature
from vitrina.structure.models import Metadata
from vitrina.users.models import User


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
        dataset_metadata_by_organization = kwargs.pop("dataset_metadata_by_organization", {})
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

            choice_name = metadata.name
            choices.extend(
                [
                    (f"uapi:/{choice_name}/:getall", f"uapi:/{choice_name}/:getall"),
                    (f"uapi:/{choice_name}/:search", f"uapi:/{choice_name}/:search"),
                    (f"uapi:/{choice_name}/:select", f"uapi:/{choice_name}/:select"),
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
        self.helper.add_input(Submit("submit", _("Įkelti dokumentą"), css_class="button is-primary"))

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


class AgreementGeneratePdfForm(forms.Form):
    template = forms.ModelChoiceField(
        label=_("Pasirinkite šabloną (privaloma)"),
        queryset=SmartContractTemplate.objects.none(),  # will be dynamically set in __init__
        required=True,
    )
    other_assigner_legislations = forms.CharField(
        label=_("Papildomi teikėjo teisės aktai"),
        required=False,
        widget=forms.Textarea(),
    )
    payment_terms = forms.CharField(label=_("Mokėjimo sąlygos"), required=False, widget=forms.Textarea())
    assigner_representative = forms.ModelChoiceField(
        label=_("Duomenų teikėjo atstovas"),
        queryset=Contact.objects.none(),
        required=True,
    )
    assignee_representative = forms.ModelChoiceField(
        label=_("Duomenų gavėjo atstovas"), queryset=Contact.objects.none(), required=True
    )

    @cached_property
    def content_type_user(self) -> QuerySet[ContentType]:
        return ContentType.objects.get_for_model(User)

    def __init__(self, *args, **kwargs):
        agreement: Agreement = kwargs.pop("agreement")
        super().__init__(*args, **kwargs)

        self.fields["template"].queryset = SmartContractTemplate.objects.filter(
            Q(organization__isnull=True) | Q(organization=agreement.assigner)
        ).order_by("organization", "file")

        self.fields["assigner_representative"].queryset = self.get_contact_queryset(agreement.assigner)
        self.fields["assignee_representative"].queryset = self.get_contact_queryset(agreement.assignee)

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Generuoti sutarties dokumentą"), css_class="button is-primary"))

    def get_contact_queryset(self, organization: Organization) -> QuerySet[Contact]:
        user_ids = User.objects.filter(Q(organization=organization.pk), Q(deleted=False) | Q(deleted="")).values_list(
            "pk", flat=True
        )

        return Contact.objects.filter(content_type=self.content_type_user, object_id__in=user_ids)
