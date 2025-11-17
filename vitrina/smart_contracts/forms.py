from functools import cached_property

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Q, QuerySet
from django.core.files.uploadedfile import UploadedFile
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _
import zipfile

from vitrina.datasets.models import Contact
from vitrina.orgs.models import Organization
from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.models import (
    AgreementFile,
    SmartContractTemplate,
    Agreement,
    AgreementStatuses,
)
from vitrina.smart_contracts.services import (
    is_valid_adoc,
    get_signers_from_adoc,
    get_pdf_path_in_adoc,
    generate_checksum,
    num_of_adoc_root_files,
)
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
        self.agreement_pdf: AgreementFile = kwargs.pop("agreement_pdf")
        self.agreement: Agreement = kwargs.pop("agreement")
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

    def clean_file(self) -> UploadedFile:
        file = self.cleaned_data["file"]
        try:
            with zipfile.ZipFile(file) as zip_file:
                if not is_valid_adoc(zip_file):
                    raise InvalidAdocError("Neteisingas ADOC formatas.")
                if num_of_adoc_root_files(zip_file) > 1:
                    raise InvalidAdocError(_("Rastas daugiau nei vienas pasirašytas dokumentas."))
                if not (pdf_path := get_pdf_path_in_adoc(zip_file)):
                    raise InvalidAdocError(_("Nerastas PDF dokumentas."))
                with zip_file.open(pdf_path) as pdf_file:
                    pdf_bytes = pdf_file.read()
                if generate_checksum(pdf_bytes) != self.agreement_pdf.checksum:
                    raise InvalidAdocError(_("PDF dokumentas nesutampa su sutartyje esančiu PDF dokumentu."))
                signers_in_adoc = [signer.full_name for signer in get_signers_from_adoc(zip_file)]
        except (InvalidAdocError, zipfile.BadZipFile) as error:
            raise ValidationError(f"ADOC klaida: {str(error)}")

        num_of_signers = len(signers_in_adoc)
        signers_to_find = [self.agreement.assignee_representative_full_name]

        if num_of_signers == 0:
            raise ValidationError(_("Įkelta sutartis nepasirašyta."))

        if self.agreement.status == AgreementStatuses.FORMED:
            if num_of_signers > 1:
                raise ValidationError(
                    _("Įkelta sutartis pasirašyta daugiau nei 1 parašu. Gavėjas turėtų pasirašyti tik vienu parašu.")
                )
        elif self.agreement.status == AgreementStatuses.INITIATED:
            if num_of_signers == 1:
                raise ValidationError(_("Įkelta sutartis nepasirašyta teikėjo parašu."))
            if num_of_signers > 2:
                raise ValidationError(_("Įkeltoje sutartyje rasti daugiau nei 2 parašai."))
            signers_to_find.append(self.agreement.assigner_representative_full_name)
        else:
            raise ValidationError(
                _("Pasirašyti galima tik sutartis su būsenomis `{formed}` arba `{initiated}`.").format(
                    formed=AgreementStatuses.FORMED, initiated=AgreementStatuses.INITIATED
                )
            )
        if not all(signer in signers_in_adoc for signer in signers_to_find):
            raise ValidationError(
                _(
                    "Nesutampa pasirašiusių asmenų vardai ir pavardės. "
                    "Reikalingi parašai: {expected}, ADOC rasti parašai: {found}."
                ).format(
                    expected=signers_to_find,
                    found=signers_in_adoc,
                )
            )
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
