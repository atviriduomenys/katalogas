import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.urls import reverse
from django_webtest import DjangoTestApp
from pdfminer.high_level import extract_text

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.smart_contracts.models import (
    Agreement,
    AgreementScope,
    AgreementFile,
    SmartContractTemplate,
)
from vitrina.structure.factories import MetadataFactory
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db
test_contracts_dir = Path(__file__).parent / "files" / "test_contracts"


class TestAgreementListView:
    def test_cannot_list_without_permission(self, app: DjangoTestApp) -> None:
        user = UserFactory()
        project = ProjectFactory()
        app.set_user(user)

        response = app.get(
            reverse("agreement-list", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 403

    def test_list_agreements(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset])
        app.set_user(user)
        AgreementFactory(project=project, assigner=organization)

        response = app.get(reverse("agreement-list", args=[project.pk]))

        assert response.status_code == 200
        assert response.context["agreements"].count() == 1

    def test_list_no_agreements(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset])
        app.set_user(user)

        response = app.get(reverse("agreement-list", args=[project.pk]))

        assert response.status_code == 200
        assert response.context["agreements"].count() == 0


class TestAgreementDetailView:
    def test_cannot_show_details_without_permission(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        user = UserFactory()
        app.set_user(user)
        project = ProjectFactory()
        agreement = AgreementFactory(project=project, assigner=organization)

        response = app.get(
            reverse("agreement-detail", args=[project.pk, agreement.pk]),
            expect_errors=True,
        )
        assert response.status_code == 403

    def test_http_404_when_agreement_does_not_exist(self, app: DjangoTestApp) -> None:
        user = UserFactory()
        app.set_user(user)
        project = ProjectFactory()

        response = app.get(
            reverse("agreement-detail", args=[project.pk, uuid4()]), expect_errors=True
        )
        assert response.status_code == 404

    def test_http_404_when_agreement_does_not_exist_in_project(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(project=project, assigner=organization)
        different_project = ProjectFactory()

        response = app.get(
            reverse("agreement-detail", args=[different_project.pk, agreement.pk]),
            expect_errors=True,
        )
        assert response.status_code == 404

    def test_agreement_details(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(project=project, assigner=organization)

        response = app.get(reverse("agreement-detail", args=[project.pk, agreement.pk]))
        assert response.status_code == 200
        assert response.context["agreement"] == agreement


class TestAgreementCreateView:
    def test_cannot_create_agreement_without_permission(
        self, app: DjangoTestApp
    ) -> None:
        user = UserFactory()
        project = ProjectFactory()
        app.set_user(user)

        response = app.get(
            reverse("agreement-create", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 403

    def test_cannot_create_agreement_for_deleted_project(
        self, app: DjangoTestApp
    ) -> None:
        user = UserFactory()
        project = ProjectFactory(user=user, deleted=True)
        app.set_user(user)

        response = app.get(
            reverse("agreement-create", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 404

    def test_cannot_create_agreements_if_all_organizations_already_has_agreement(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user)
        AgreementFactory(project=project, assigner=organization)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        assert response.status_code == 302
        assert response.url == reverse("agreement-list", args=[project.pk])

    def test_creates_agreement_and_scopes(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset], organization=organization)
        ct = ContentType.objects.get_for_model(Organization)
        RepresentativeFactory(user=user, content_type=ct, object_id=organization.pk)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]
        form["form-0-scopes"] = ["uapi:/test/dataset/:getall"]
        response = form.submit()

        assert response.status_code == 302
        assert response.url == reverse("agreement-list", args=[project.pk])

        agreement = Agreement.objects.get(project=project, assigner=organization)
        assert agreement.status == AgreementStatuses.CREATED
        assert agreement.is_agent_sync_enabled is False
        assert agreement.scopes.count() == 1

        agreement_scope = agreement.scopes.first()
        assert agreement_scope.resource == "uapi:/test/dataset"
        assert agreement_scope.action == "getall"
        assert agreement_scope.scope == "uapi:/test/dataset/:getall"

    def test_creates_multiple_agreements_and_scopes(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        dataset1 = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset1),
            object_id=dataset1.pk,
            dataset=dataset1,
            name="test/dataset1",
        )
        dataset2 = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset2),
            object_id=dataset2.pk,
            dataset=dataset2,
            name="test/dataset2",
        )
        diff_organization = OrganizationFactory()
        diff_dataset = DatasetFactory(organization=diff_organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(diff_dataset),
            object_id=diff_dataset.pk,
            dataset=diff_dataset,
            name="datasets/gov/org/dataset",
        )
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset1, dataset2, diff_dataset], organization=organization)
        ct = ContentType.objects.get_for_model(Organization)
        RepresentativeFactory(user=user, content_type=ct, object_id=organization.pk)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]
        form["form-0-scopes"] = [
            "uapi:/test/dataset1/:getall",
            "uapi:/test/dataset2/:search",
            "uapi:/test/dataset2/:select",
        ]
        form["form-1-scopes"] = ["uapi:/datasets/gov/org/dataset/:getall"]
        response = form.submit()

        assert response.status_code == 302
        assert response.url == reverse("agreement-list", args=[project.pk])

        assert Agreement.objects.filter(project=project).count() == 2
        assert set(
            AgreementScope.objects.filter(agreement__assigner=organization).values_list(
                "scope", flat=True
            )
        ) == {"uapi:/test/dataset1/:getall", "uapi:/test/dataset2/:search", "uapi:/test/dataset2/:select"}
        assert set(
            AgreementScope.objects.filter(
                agreement__assigner=diff_organization
            ).values_list("scope", flat=True)
        ) == {"uapi:/datasets/gov/org/dataset/:getall"}

    def test_can_create_agreements_for_organizations_that_currently_do_not_have_one(
        self, app: DjangoTestApp, dataset: Dataset, organization: Organization
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        organization2 = OrganizationFactory()
        dataset2 = DatasetFactory(organization=organization2)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset2),
            object_id=dataset2.pk,
            dataset=dataset2,
            name="test/dataset2",
        )
        project = ProjectFactory(user=user, datasets=[dataset, dataset2], organization=organization)
        ct = ContentType.objects.get_for_model(Organization)
        RepresentativeFactory(user=user, content_type=ct, object_id=organization.pk)
        AgreementFactory(project=project, assigner=organization)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]

        assert form.fields.get("form-0-scopes")
        assert not form.fields.get("form-1-scopes")

    def test_cannot_create_agreement_with_invalid_scopes(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset], organization=organization)
        ct = ContentType.objects.get_for_model(Organization)
        RepresentativeFactory(user=user, content_type=ct, object_id=organization.pk)
        app.set_user(user)

        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-id": organization.id,
            "form-0-scopes": ["bad_scope"],
        }
        response = app.post(reverse("agreement-create", args=[project.pk]), data)

        assert response.status_code == 200
        assert Agreement.objects.filter(project=project).count() == 0

    def test_create_agreement_for_personal_project(
        self, app: DjangoTestApp, dataset: Dataset
    ) -> None:
        user = UserFactory()
        project = ProjectFactory(user=user, datasets=[dataset])
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]), status=403)

        assert response.status_code == 403

    def test_create_for_organization_project_mid_change_to_personal(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset], organization=organization)
        ct = ContentType.objects.get_for_model(Organization)
        RepresentativeFactory(user=user, content_type=ct, object_id=organization.pk)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]
        form["form-0-scopes"] = ["uapi:/test/dataset/:getall"]
        project.organization = None
        project.save()
        response = form.submit()

        assert response.status_code == 302
        assert response.url == reverse("agreement-list", args=[project.pk])

        assert not Agreement.objects.filter(project=project).exists()


class TestAgreementGeneratePdf:
    def test_cannot_generate_pdf_without_permission(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        user = UserFactory()
        app.set_user(user)
        project = ProjectFactory()
        agreement = AgreementFactory(project=project, assigner=organization)

        response = app.get(
            reverse("agreement-generate-pdf", args=[project.pk, agreement.pk]),
            expect_errors=True,
        )
        assert response.status_code == 403

    def test_page_loads_without_error(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset,
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(
            project=project, assigner=organization, status=AgreementStatuses.CREATED,
        )

        response = app.get(
            reverse("agreement-generate-pdf", args=[project.pk, agreement.pk]),
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "status",
        [
            AgreementStatuses.FORMED,
            AgreementStatuses.INITIATED,
            AgreementStatuses.SIGNED,
            AgreementStatuses.ACTIVE,
            AgreementStatuses.TERMINATED,
        ],
    )
    def test_cannot_generate_pdf_for_agreement_with_status_other_than_created(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        status: AgreementStatuses,
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(
            project=project, assigner=organization, status=status
        )
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        response = app.post(
            reverse("agreement-generate-pdf", args=[project.pk, agreement.pk]),
            {
                "template": template.pk,
                "other_assigner_legislations": "",
                "other_assignee_legislations": "",
                "payment_terms": "",
            },
        )

        agreement.refresh_from_db()
        assert response.status_code == 302
        assert agreement.status == status

    def test_generate_pdf_changes_agreement_status_to_formed(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )
        user = UserFactory(organization=organization, email="bethgarcia@example.net")
        app.set_user(user)

        organization.title = "Gonzalez Group"
        organization.company_code = "LWGYU0W8S"
        organization.address = "206 Weaver Trace\nNorth Danny, VA 96120"
        organization.email = "lwolf@example.com"
        organization.phone = "456.631.4059"
        organization.save()

        dataset.title = "Odit nostrum."
        dataset.save()

        project = ProjectFactory(user=user, datasets=[dataset])

        agreement = AgreementFactory(
            project=project,
            assigner=organization,
            assignee=organization,
            created_by=user,
            status=AgreementStatuses.CREATED,
        )

        assert agreement.files.count() == 0
        other_assigner_legislations = "Bought data"
        other_assignee_legislations = "Sold data"
        payment_terms = "Cash only"
        response = app.post(
            reverse("agreement-generate-pdf", args=[project.pk, agreement.pk]),
            {
                "template": template.pk,
                "other_assigner_legislations": other_assigner_legislations,
                "other_assignee_legislations": other_assignee_legislations,
                "payment_terms": payment_terms,
            },
        )
        agreement.refresh_from_db()
        assert response.status_code == 302
        assert agreement.status == AgreementStatuses.FORMED
        agreement_files = list(agreement.files.order_by("is_template", "created_at"))
        assert len(agreement_files) == 3
        contract: AgreementFile = agreement_files[1]
        template_copy: AgreementFile = agreement_files[2]
        odlr_file: AgreementFile = agreement_files[0]


        assert template_copy.is_template
        assert template_copy.file_name
        for name_part in ("_copy.md", "contract_template"):
            assert name_part in template_copy.file_name
        assert "/" not in template_copy.file_name
        assert template_copy.file.path != template.file.path  # check if is an hard copy
        assert template_copy.file.read() == template.file.read()
        assert template_copy.checksum

        assert odlr_file.file_name.endswith(".json")

        assert not contract.is_template
        assert contract.checksum

        odrl :dict= json.loads(odlr_file.file.read())

        expected_odrl = {
            "@context": {
                "@vocab": "http://www.w3.org/ns/odrl.jsonld",
                "ex": "http://example.org/vocab#",
            },
            "uid": f"https://data.gov.lt/ID/datasets/gov/vssa/isris/dcat/Agreement/{agreement.pk}",
            "type": "Agreement",
            "profile": "http://www.w3.org/ns/odrl/profile/core",
            "issued": odrl[
                "issued"
            ],  # Use actual value from file to avoid time mismatch
            "assigner": [
                {
                    "uid": str(organization.pk),
                    "ex:companyName": "Gonzalez Group",
                    "ex:companyCode": "LWGYU0W8S",
                    "ex:address": "206 Weaver Trace\nNorth Danny, VA 96120",
                    "ex:representative": " - ",
                    "ex:email": "lwolf@example.com",
                    "ex:phone": "456.631.4059",
                    "ex:personalCode": " - ",
                }
            ],
            "assignee": [
                {
                    "uid": str(organization.pk),
                    "ex:companyName": "Gonzalez Group",
                    "ex:companyCode": "LWGYU0W8S",
                    "ex:address": "206 Weaver Trace\nNorth Danny, VA 96120",
                    "ex:representative": " - ",
                    "ex:email": "lwolf@example.com",
                    "ex:phone": "456.631.4059",
                    "ex:personalCode": " - ",
                }
            ],
            "permission": [
                {
                    "target": {
                        "uid": dataset.pk,
                        "ex:name": "Odit nostrum.",
                        "ex:scopes": [],
                    }
                }
            ],
            "ex:paymentTerms": payment_terms,
            "ex:otherAssignerLegislations": other_assigner_legislations,
            "ex:otherAssigneeLegislations": other_assignee_legislations,
        }

        assert odrl == expected_odrl
        assert contract.file
        assert contract.file_name
        contract.file.seek(0)
        pdf_text = extract_text(BytesIO(contract.file.read()))

        # Pull specific expected values directly from the odrl JSON
        expected_values = [
            # Dates
            odrl["issued"],  # Check only date portion to avoid microsecond mismatches
            # Assigner
            odrl["assigner"][0]["ex:companyName"],
            odrl["assigner"][0]["ex:companyCode"],
            odrl["assigner"][0]["ex:address"].split("\n")[0],  # Just street line
            odrl["assigner"][0]["ex:email"],
            odrl["assigner"][0]["ex:phone"],
            odrl["assigner"][0]["ex:representative"],
            odrl["assigner"][0]["ex:personalCode"],
            # Assignee
            odrl["assignee"][0]["ex:companyName"],
            odrl["assignee"][0]["ex:companyCode"],
            odrl["assignee"][0]["ex:address"].split("\n")[0],
            odrl["assignee"][0]["ex:email"],
            odrl["assignee"][0]["ex:phone"],
            odrl["assignee"][0]["ex:representative"],
            odrl["assignee"][0]["ex:personalCode"],
            # Permission target
            odrl["permission"][0]["target"]["ex:name"],
            *odrl["permission"][0]["target"].get("ex:scopes", []),
            # Misc fields
            odrl["ex:paymentTerms"],
            odrl["ex:otherAssignerLegislations"],
            odrl["ex:otherAssigneeLegislations"],
        ]

        # Validate that each expected value appears in the PDF text
        for i, value in enumerate(expected_values):
            value = str(value).strip()
            if value:
                assert value in pdf_text, (
                    f"Expected '{value}' (index={i}) not found in PDF"
                )


class TestAgreementUploadSignedFile:
    def test_cannot_upload_adoc_without_permission(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        user = UserFactory()
        app.set_user(user)
        project = ProjectFactory()
        agreement = AgreementFactory(
            project=project, assigner=organization, status=AgreementStatuses.FORMED
        )

        response = app.get(
            reverse("agreement-upload-signed-adoc", args=[project.pk, agreement.pk]),
            expect_errors=True,
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "status",
        [
            AgreementStatuses.CREATED,
            AgreementStatuses.SIGNED,
            AgreementStatuses.ACTIVE,
            AgreementStatuses.TERMINATED,
        ],
    )
    def test_cannot_upload_adoc_for_agreement_with_statuses_other_than_formed_initiated(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        status: AgreementStatuses,
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(
            project=project, assigner=organization, status=status
        )

        response = app.get(
            reverse("agreement-upload-signed-adoc", args=[project.pk, agreement.pk])
        )
        agreement.refresh_from_db()
        assert response.status_code == 302
        assert agreement.status == status

    def test_upload_adoc_and_change_status_to_initiated_if_agreement_status_formed(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(
            project=project, assigner=organization, status=AgreementStatuses.FORMED
        )

        file_path = str(test_contracts_dir / "sutartis_signed.adoc")
        response = app.get(
            reverse("agreement-upload-signed-adoc", args=[project.pk, agreement.pk]),
        )
        with open(file_path, "rb") as f:
            form = response.forms["agreement-upload-form"]
            form["file"] = (file_path, f.read())
            form.submit()

        agreement.refresh_from_db()
        assert response.status_code == 200
        assert agreement.status == AgreementStatuses.INITIATED
        assert not agreement.is_agent_sync_enabled
        assert agreement.files.exists()

    def test_upload_adoc_and_change_status_to_signed_if_agreement_status_initiated(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(
            project=project, assigner=organization, status=AgreementStatuses.INITIATED
        )

        file_path = str(test_contracts_dir / "sutartis_signed.adoc")
        response = app.get(
            reverse("agreement-upload-signed-adoc", args=[project.pk, agreement.pk]),
        )
        with open(file_path, "rb") as f:
            form = response.forms["agreement-upload-form"]
            form["file"] = (file_path, f.read())
            form.submit()

        agreement.refresh_from_db()
        assert response.status_code == 200
        assert agreement.status == AgreementStatuses.SIGNED
        assert agreement.is_agent_sync_enabled
        assert agreement.files.exists()
