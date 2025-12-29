from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from authlib.jose import RSAKey
from django.conf import settings
from django.urls import reverse
from django_webtest import DjangoTestApp
from rest_framework import status

from tests.uapi.conftest import _generate_test_token
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory, UseCaseClientFactory
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory, AgreementFileFactory
from vitrina.smart_contracts.models import Agreement

pytestmark = pytest.mark.django_db
timezone = ZoneInfo(settings.TIME_ZONE)


def use_case_url() -> str:
    return reverse("uapi-usecase")


def use_case_detail_url(use_case_uuid: UUID) -> str:
    return reverse("uapi-usecase-detail", kwargs={"use_case_uuid": use_case_uuid})


def create_agreement(
    use_case: Project,
    assigner_organization: Organization,
    assignee_organization: Organization = None,
    status: AgreementStatuses = AgreementStatuses.ACTIVE
) -> Agreement:
    if assignee_organization is None:
        assignee_organization = OrganizationFactory()
    return AgreementFactory(
        assigner=assigner_organization, assignee=assignee_organization, project=use_case, status=status
    )


class TestUseCaseViewSetAuthorization:
    def test_401_if_unauthorized(self, app: DjangoTestApp):
        response = app.get(use_case_url(), expect_errors=True)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_403_if_token_has_no_organization(self, app: DjangoTestApp, organization: Organization, test_jwk: RSAKey):
        token = _generate_test_token(test_jwk, organization=None, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)
        response = app.get(
            use_case_url(),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "invalid_scopes", [
            tuple(),
            ("", ),
            ("invalid_scope1", "invalid_scope2"),

        ])
    def test_403_if_list_authorized_with_incorrect_scopes(
        self, app: DjangoTestApp, organization: Organization, test_jwk: RSAKey, invalid_scopes: tuple[str]
    ):
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)
        response = app.get(
            use_case_url(),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "invalid_scopes", [
            tuple(),
            ("", ),
            ("invalid_scope1", "invalid_scope2"),

        ])
    def test_403_if_retrieve_authorized_with_incorrect_scopes(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        test_jwk: RSAKey,
        invalid_scopes: tuple[str],
    ):
        use_case = ProjectFactory(organization=organization, datasets=[dataset])
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)
        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUseCaseViewSetList:
    def test_404_if_use_case_in_different_organization(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        different_organization = OrganizationFactory()
        use_case = ProjectFactory(datasets=[dataset])
        create_agreement(use_case, assigner_organization=different_organization, assignee_organization=organization)
        response = app.get(
            use_case_url(),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_404_if_use_case_has_no_agreement(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        ProjectFactory(datasets=[dataset])
        response = app.get(
            use_case_url(),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "incorrect_status", [
            AgreementStatuses.CREATED,
            AgreementStatuses.SUBMITTED,
            AgreementStatuses.APPROVED,
            AgreementStatuses.FORMED,
            AgreementStatuses.INITIATED,
            AgreementStatuses.TERMINATED,
        ]
    )
    def test_404_if_use_case_has_agreement_with_incorrect_status(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        valid_token: str,
        incorrect_status: AgreementStatuses,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        create_agreement(use_case, organization, status=incorrect_status)
        response = app.get(
            use_case_url(),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("correct_status", [AgreementStatuses.SIGNED, AgreementStatuses.ACTIVE])
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        valid_token: str,
        correct_status: AgreementStatuses,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        create_agreement(use_case, organization, status=correct_status)
        response = app.get(
            use_case_url(),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_type": "/uapi/datasets/org/vssa/isris/dcat/UseCase",
            "_data": [
                {
                    "uuid": str(use_case.uuid),
                    "_type": "/uapi/datasets/org/vssa/isris/dcat/UseCase",
                    "_id": str(use_case.id),
                    "_revision": "",
                    "_txn": "",
                    "_created": use_case.created.astimezone(timezone).isoformat(),
                    "_updated": use_case.modified.astimezone(timezone).isoformat(),
                    "@context": ""
                }
            ]
        }

    def test_filter_use_cases_with_given_dataset_uuid(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        dataset2 = DatasetFactory()
        use_case1 = ProjectFactory(datasets=[dataset])
        use_case2 = ProjectFactory(datasets=[dataset, dataset2])
        use_case3 = ProjectFactory(datasets=[dataset2])
        create_agreement(use_case1, organization)
        create_agreement(use_case2, organization)
        create_agreement(use_case3, organization)
        response = app.get(
            f"{use_case_url()}?dataset={dataset.uuid}",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert {use_case_data["uuid"] for use_case_data in response.json["_data"]} == {
            str(use_case1.uuid), str(use_case2.uuid)
        }

    def test_filter_use_cases_with_multiple_given_dataset_uuids(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        dataset2 = DatasetFactory()
        use_case1 = ProjectFactory(datasets=[dataset])
        use_case2 = ProjectFactory(datasets=[dataset2])
        use_case3 = ProjectFactory(datasets=[DatasetFactory()])
        create_agreement(use_case1, organization)
        create_agreement(use_case2, organization)
        create_agreement(use_case3, organization)
        response = app.get(
            f"{use_case_url()}?dataset={dataset.uuid}&dataset={dataset2.uuid}",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert {use_case_data["uuid"] for use_case_data in response.json["_data"]} == {
            str(use_case1.uuid), str(use_case2.uuid)
        }


class TestUseCaseViewSetRetrieve:
    def test_404_if_use_case_in_different_organization(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        different_organization = OrganizationFactory()
        use_case = ProjectFactory(datasets=[dataset])
        create_agreement(use_case, assigner_organization=different_organization, assignee_organization=organization)

        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_404_if_use_case_has_no_agreement(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        use_case = ProjectFactory(datasets=[dataset])

        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "incorrect_status", [
            AgreementStatuses.CREATED,
            AgreementStatuses.SUBMITTED,
            AgreementStatuses.APPROVED,
            AgreementStatuses.FORMED,
            AgreementStatuses.INITIATED,
            AgreementStatuses.TERMINATED,
        ]
    )
    def test_404_if_use_case_has_no_agreement_with_correct_status(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        valid_token: str,
        incorrect_status: AgreementStatuses,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        create_agreement(use_case, organization, status=incorrect_status)

        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_404_if_use_case_with_given_uuid_does_not_exist(self, app: DjangoTestApp, valid_token: str):
        response = app.get(
            use_case_detail_url(uuid4()),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_success(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement1 = create_agreement(use_case, organization, status=AgreementStatuses.SIGNED)
        agreement2 = create_agreement(use_case, organization, status=AgreementStatuses.ACTIVE)
        use_case_client1 = UseCaseClientFactory(use_case=use_case)
        use_case_client2 = UseCaseClientFactory(use_case=use_case)
        agreement_file1 = AgreementFileFactory(agreement=agreement1)
        agreement_file2 = AgreementFileFactory(agreement=agreement2)

        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        agreement_file_url1 = reverse(
            "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file1.uuid}
        )
        agreement_file_url2 = reverse(
            "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file2.uuid}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "uuid": str(use_case.uuid),
            "agreements": {
                str(agreement1.uuid): {"file_url": f"http://testserver{agreement_file_url1}"},
                str(agreement2.uuid): {"file_url": f"http://testserver{agreement_file_url2}"},
            },
            "contract_scopes": {
                str(agreement1.uuid): [
                    "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                    "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                ],
                str(agreement2.uuid): [
                    "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                    "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                ]
            },
            "clients": [str(use_case_client1.uuid), str(use_case_client2.uuid)],
            "_type": "",
            "_id": str(use_case.id),
            "_revision": "",
            "_txn": "",
            "_created": use_case.created.astimezone(timezone).isoformat(),
            "_updated": use_case.modified.astimezone(timezone).isoformat(),
            "@context": ""
        }

    def test_return_only_agreements_that_are_ready_to_be_synced(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        use_case = ProjectFactory(datasets=[dataset])
        # Ready to be synced
        agreement1 = create_agreement(use_case, organization, status=AgreementStatuses.SIGNED)
        AgreementFileFactory(agreement=agreement1)
        agreement2 = create_agreement(use_case, organization, status=AgreementStatuses.ACTIVE)
        AgreementFileFactory(agreement=agreement2)

        # Not ready to be synced
        different_organization = OrganizationFactory()
        # Bad organization
        agreement3 = create_agreement(
            use_case, assigner_organization=different_organization, assignee_organization=organization
        )
        AgreementFileFactory(agreement=agreement3)
        # Bad agreement status
        agreement4 = create_agreement(use_case, organization, status=AgreementStatuses.FORMED)
        AgreementFileFactory(agreement=agreement4)
        # No agreement file
        create_agreement(use_case, organization)

        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert set(response.json["agreements"].keys()) == {str(agreement1.uuid), str(agreement2.uuid)}
        assert set(response.json["contract_scopes"].keys()) == {str(agreement1.uuid), str(agreement2.uuid)}

    def test_return_latest_agreement_adoc_if_there_are_multiple(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement = create_agreement(use_case, organization)
        AgreementFileFactory(agreement=agreement)
        agreement_file2 = AgreementFileFactory(agreement=agreement)

        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        agreement_file_url2 = reverse(
            "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file2.uuid}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json["agreements"][str(agreement.uuid)] == {
            "file_url": f"http://testserver{agreement_file_url2}"
        }

    def test_raise_error_if_contract_scope_extraction_fails(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement = create_agreement(use_case, organization)
        agreement_file = AgreementFileFactory(
            agreement=agreement,
            file_path=settings.BASE_DIR / "tests/smart_contracts/files/test_contracts/agreement_no_pdf.adoc"
        )

        response = app.get(
            use_case_detail_url(use_case.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json == {
            "code": "smart_contract_parse_error",
            "type": "SmartContractParseError",
            "template": "One of smart contract files cannot be parsed.",
            "message": (
                f"Agreement (uuid={agreement.uuid}) file (uuid={agreement_file.uuid}) cannot be parsed. "
                f"Reason: Invalid ADOC file: 'There is no item named None in the archive'"
            ),
            "additionalProperties": None,
        }
