from uuid import UUID, uuid4

import pytest
from authlib.jose import RSAKey
from django.conf import settings
from django.urls import reverse
from django_webtest import DjangoTestApp
from rest_framework import status

from tests.uapi.conftest import _generate_test_token
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFileFactory, AgreementFactory


def agreement_file_url(agreement_file_uuid: UUID) -> str:
    return reverse("uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file_uuid})


class TestAgreementFileDownloadUAPIView:
    def test_403_if_unauthorized(self, app: DjangoTestApp):
        response = app.get(agreement_file_url(agreement_file_uuid=uuid4()), expect_errors=True)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_403_if_token_has_no_organization(self, app: DjangoTestApp, organization: Organization, test_jwk: RSAKey):
        token = _generate_test_token(test_jwk, organization=None, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)
        response = app.get(
            agreement_file_url(agreement_file_uuid=uuid4()),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "invalid_scopes",
        [
            tuple(),
            ("",),
            ("invalid_scope1", "invalid_scope2"),
        ],
    )
    def test_403_if_list_authorized_with_incorrect_scopes(
        self, app: DjangoTestApp, organization: Organization, test_jwk: RSAKey, invalid_scopes: tuple[str]
    ):
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)
        response = app.get(
            agreement_file_url(agreement_file_uuid=uuid4()),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_404_if_agreement_file_in_different_organization(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        different_organization = OrganizationFactory()
        use_case = ProjectFactory(organization=different_organization, datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=different_organization, status=AgreementStatuses.SIGNED)
        agreement_file = AgreementFileFactory(agreement=agreement)

        response = app.get(
            agreement_file_url(agreement_file.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "incorrect_status",
        [
            AgreementStatuses.CREATED,
            AgreementStatuses.SUBMITTED,
            AgreementStatuses.APPROVED,
            AgreementStatuses.FORMED,
            AgreementStatuses.INITIATED,
            AgreementStatuses.TERMINATED,
        ],
    )
    def test_404_if_use_case_has_no_agreement_with_correct_status(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        valid_token: str,
        incorrect_status: AgreementStatuses,
    ):
        use_case = ProjectFactory(organization=organization, datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=incorrect_status)
        agreement_file = AgreementFileFactory(agreement=agreement)

        response = app.get(
            agreement_file_url(agreement_file.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_404_if_agreement_file_not_adoc(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset, valid_token: str
    ):
        use_case = ProjectFactory(organization=organization, datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement_file = AgreementFileFactory(
            agreement=agreement,
            file_path=settings.BASE_DIR / "tests/smart_contracts/files/test_contracts/agreement.pdf",
        )

        response = app.get(
            agreement_file_url(agreement_file.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_404_if_agreement_file_with_given_uuid_does_not_exist(self, app: DjangoTestApp, valid_token: str):
        response = app.get(
            agreement_file_url(uuid4()),
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
        use_case = ProjectFactory(organization=organization, datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=correct_status)
        agreement_file = AgreementFileFactory(agreement=agreement)

        response = app.get(
            agreement_file_url(agreement_file.uuid),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("Content-Disposition") == f'attachment; filename="{agreement_file.uuid}.adoc"'
