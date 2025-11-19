from factory import SubFactory, lazy_attribute
from factory.django import DjangoModelFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from pathlib import Path

from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.models import Agreement, AgreementFile
from vitrina.users.factories import UserFactory
from vitrina.datasets.factories import ContactFactory


class AgreementFactory(DjangoModelFactory):
    class Meta:
        model = Agreement
        django_get_or_create = ("project", "assigner", "assignee", "created_by")

    status = AgreementStatuses.CREATED
    assignee = SubFactory(OrganizationFactory)
    assigner = SubFactory(OrganizationFactory)
    created_by = SubFactory(UserFactory)
    project = SubFactory(ProjectFactory, organization=SubFactory(OrganizationFactory))
    assigner_representative = SubFactory(ContactFactory)
    assignee_representative = SubFactory(ContactFactory)


class AgreementPDFFileFactory(DjangoModelFactory):
    class Meta:
        model = AgreementFile

    class Params:
        pdf_path = None

    agreement = SubFactory(AgreementFactory)

    @lazy_attribute
    def file(self) -> SimpleUploadedFile:
        if self.pdf_path:
            file_path = Path(self.pdf_path)
            return SimpleUploadedFile(file_path.name, file_path.read_bytes(), content_type="application/pdf")
        return SimpleUploadedFile("dummy.pdf", b"%PDF-1.4\n", content_type="application/pdf")


class AgreementJSONFileFactory(DjangoModelFactory):
    class Meta:
        model = AgreementFile

    class Params:
        json_path = None

    agreement = SubFactory(AgreementFactory)

    @lazy_attribute
    def file(self) -> SimpleUploadedFile:
        if self.json_path:
            file_path = Path(self.json_path)
            return SimpleUploadedFile(file_path.name, file_path.read_bytes(), content_type="application/json")
        return SimpleUploadedFile("dummy.json", b"{}", content_type="application/json")
