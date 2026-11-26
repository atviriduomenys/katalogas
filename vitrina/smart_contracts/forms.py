from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Q, QuerySet
from django.core.files.uploadedfile import UploadedFile
from django.forms import CheckboxSelectMultiple
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
import zipfile

from vitrina.datasets.models import Contact, Dataset
from vitrina.orgs.models import Organization
from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.models import (
    AgreementFile,
    SmartContractTemplate,
    Agreement,
)
from vitrina.smart_contracts.services import get_signers_from_adoc, validate_adoc, validate_signatures
from vitrina.structure.models import Metadata, Model, ModelScope
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

            # The whole dataset, then each of its models' scopes, which limit the rows and columns given.
            resources = [metadata.name, *_model_scope_names(metadata.dataset)]
            choices.extend(
                (f"uapi:/{resource}/:{action}", f"uapi:/{resource}/:{action}")
                for resource in resources
                for action in SCOPE_ACTIONS
            )
        return choices


SCOPE_ACTIONS = ("getall", "getone", "search")


def _model_scope_names(dataset: Dataset | None) -> list[str]:
    """`Model/@scope` names of the dataset's models' scopes in its latest version."""
    if dataset is None or (version := dataset.latest_version()) is None:
        return []
    model_names = dict(
        Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(Model), metadata_version=version
        ).values_list("object_id", "name")
    )
    scope_refs = dict(
        Metadata.objects.filter(content_type=ContentType.objects.get_for_model(ModelScope), metadata_version=version)
        .exclude(ref__isnull=True)
        .exclude(ref="")
        .values_list("object_id", "ref")
    )
    scopes = ModelScope.objects.filter(pk__in=scope_refs, model_id__in=model_names).values_list("pk", "model_id")
    return sorted(f"{model_names[model_id]}/@{scope_refs[scope_id]}" for scope_id, model_id in scopes)


class BaseAgreementForm(forms.ModelForm):
    label = _("Pateikti")

    def __init__(self, *args, **kwargs):
        self.agreement = kwargs.pop("agreement")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", self.label, css_class="button is-primary"))

    @cached_property
    def content_type_user(self) -> ContentType:
        return ContentType.objects.get_for_model(User)

    @staticmethod
    def get_smart_contract_templates_by_organization(organization_id: int) -> QuerySet:
        return (
            SmartContractTemplate.objects.filter(
                Q(organization__isnull=True) | Q(organization_id=organization_id),
            )
            .select_related("organization")
            .order_by(
                "organization",
                "file",
            )
        )

    def get_contacts_by_organization(self, organization_id: int) -> QuerySet:
        return Contact.objects.filter(
            Q(organization_id=organization_id), Q(content_type__isnull=True) | Q(content_type=self.content_type_user)
        )


class AgreementSubmitForm(BaseAgreementForm):
    label = _("Pateikti pasiūlymą")

    class Meta:
        model = Agreement
        fields = ("assignee_representative",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.fields["assignee_representative"].required = True
        self.fields["assignee_representative"].queryset = self.get_contacts_by_organization(self.agreement.assignee_id)


class AgreementApproveForm(BaseAgreementForm):
    label = _("Patvirtinti pasiūlymą")

    class Meta:
        model = Agreement
        fields = ("template", "assigner_representative", "other_assigner_legislations")
        required_fields = ("template", "assigner_representative")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        for field in self.Meta.required_fields:
            self.fields[field].required = True

        self.fields["template"].queryset = self.get_smart_contract_templates_by_organization(self.agreement.assigner_id)
        self.fields["assigner_representative"].queryset = self.get_contacts_by_organization(self.agreement.assigner_id)


class AgreementFormForm(BaseAgreementForm):
    label = _("Formuoti sutartį")

    class Meta:
        model = Agreement
        fields = tuple()


class BaseAgreementInitiateSignForm(BaseAgreementForm):
    class Meta:
        model = AgreementFile
        fields = ("file",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.agreement_pdf: AgreementFile = kwargs.pop("agreement_pdf")
        super().__init__(*args, **kwargs)

        self.fields["file"].validators = [
            FileExtensionValidator(allowed_extensions=["adoc"], message=_("Dokumentas turi būti adoc formato."))
        ]

        self.helper.form_id = "agreement-initiate-form"

    def clean_file(self) -> UploadedFile:
        file = self.cleaned_data["file"]
        try:
            with zipfile.ZipFile(file) as zip_file:
                validate_adoc(zip_file, checksum=self.agreement_pdf.checksum)
                signers_in_adoc = get_signers_from_adoc(zip_file)
        except InvalidAdocError as error:
            raise ValidationError(_("ADOC klaida: {error}").format(error=error))
        except zipfile.BadZipFile:
            raise ValidationError(_("Prisegtas failas nėra ZIP archyvas."))

        are_signatures_valid, error = validate_signatures(signers_in_adoc, self.agreement)
        if not are_signatures_valid:
            raise ValidationError(error)

        return file


class AgreementInitiateForm(BaseAgreementInitiateSignForm):
    title = _("Įkelti pasirašytą dokumentą (Gavėjo)")


class AgreementSignForm(BaseAgreementInitiateSignForm):
    title = _("Įkelti pasirašytą dokumentą (Teikėjo)")


class SmartContractFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False
