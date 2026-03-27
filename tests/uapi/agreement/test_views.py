from datetime import datetime
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from authlib.jose import RSAKey
from django.urls import reverse
from django_webtest import DjangoTestApp
from freezegun import freeze_time
from rest_framework import status
from django.conf import settings

from tests.uapi.conftest import _generate_test_token
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory, UseCaseClientFactory
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.factories import AgreementFactory, AgreementFileFactory
from vitrina.uapi.pagination import UAPIPagination

pytestmark = pytest.mark.django_db
timezone = ZoneInfo(settings.TIME_ZONE)


class TestSyncDone:
    def test_update_404_when_agreement_does_not_exist(self, app: DjangoTestApp, valid_token: str) -> None:
        response = app.put(
            reverse("uapi-agent-sync-done", kwargs={"agreement_id": str(uuid4())}),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json == {
            "code": "not_found",
            "type": "NotFound",
            "template": "The requested resource was not found.",
            "message": "No Agreement matches the given query.",
            "additionalProperties": None,
        }

    def test_update_404_when_different_organization_in_token(
        self,
        app: DjangoTestApp,
        organization: Organization,
        project: Project,
        valid_token: str,
    ) -> None:
        different_organization = OrganizationFactory()
        agreement = AgreementFactory(project=project, assigner=organization, assignee=different_organization)

        response = app.put(
            reverse("uapi-agent-sync-done", kwargs={"agreement_id": agreement.pk}),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json == {
            "code": "not_found",
            "type": "NotFound",
            "template": "The requested resource was not found.",
            "message": "No Agreement matches the given query.",
            "additionalProperties": None,
        }

    def test_update_404_when_agreement_sync_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        project: Project,
        valid_token: str,
    ) -> None:
        agreement = AgreementFactory(
            project=project,
            assigner=organization,
            assignee=organization,
            is_agent_sync_enabled=False,
        )

        response = app.put(
            reverse("uapi-agent-sync-done", kwargs={"agreement_id": agreement.pk}),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json == {
            "code": "not_found",
            "type": "NotFound",
            "template": "The requested resource was not found.",
            "message": "No Agreement matches the given query.",
            "additionalProperties": None,
        }

    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        project: Project,
        valid_token_disabled_agent: str,
    ):
        agreement = AgreementFactory(
            project=project,
            assigner=organization,
            assignee=organization,
            is_agent_sync_enabled=True,
        )

        response = app.put(
            reverse("uapi-agent-sync-done", kwargs={"agreement_id": agreement.pk}),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token_disabled_agent}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "The agent is disabled. Enable the agent in the Data catalog to access this API.",
            "additionalProperties": None,
        }

    def test_sync_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        project: Project,
        valid_token_disabled_agent: str,
    ):
        agreement = AgreementFactory(
            project=project,
            assigner=organization,
            assignee=organization,
            is_agent_sync_enabled=True,
        )

        response = app.put(
            reverse("uapi-agent-sync-done", kwargs={"agreement_id": agreement.pk}),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token_disabled_agent}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "The agent is disabled. Enable the agent in the Data catalog to access this API.",
            "additionalProperties": None,
        }

    def test_updates_last_sync_date_and_status_to_active(
        self,
        app: DjangoTestApp,
        organization: Organization,
        project: Project,
        valid_token: str,
    ) -> None:
        agreement = AgreementFactory(
            project=project,
            assigner=organization,
            assignee=organization,
            is_agent_sync_enabled=True,
        )

        response = app.put(
            reverse("uapi-agent-sync-done", kwargs={"agreement_id": agreement.pk}),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        agreement.refresh_from_db()
        assert agreement.last_sync_date
        assert agreement.status == AgreementStatuses.ACTIVE

    def test_does_not_update_agreement_updated_at(
        self,
        app: DjangoTestApp,
        organization: Organization,
        project: Project,
        test_jwk: RSAKey,
    ) -> None:
        creation_date = datetime(2024, 3, 3, 12, tzinfo=timezone)
        with freeze_time(creation_date):
            agreement = AgreementFactory(
                project=project,
                assigner=organization,
                assignee=organization,
                is_agent_sync_enabled=True,
            )

        with freeze_time(datetime(2024, 5, 5, 12, tzinfo=timezone)):
            token = _generate_test_token(
                test_jwk,
                organization=organization,
                scopes=["uapi:/datasets/gov/vssa/dcat/Agreement/:patch"],
            )
            response = app.put(
                reverse("uapi-agent-sync-done", kwargs={"agreement_id": agreement.pk}),
                extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        agreement.refresh_from_db()
        assert agreement.updated_at == creation_date


class TestAgreementViewSetAuthorization:
    def test_401_if_unauthorized(self, app: DjangoTestApp, agreement_url: str):
        response = app.get(agreement_url, expect_errors=True)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_403_if_token_has_no_organization(
        self, app: DjangoTestApp, organization: Organization, test_jwk: RSAKey, agreement_url: str
    ):
        token = _generate_test_token(test_jwk, organization=None, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)
        response = app.get(
            agreement_url,
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
        self,
        app: DjangoTestApp,
        organization: Organization,
        test_jwk: RSAKey,
        agreement_url: str,
        invalid_scopes: tuple[str],
    ):
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAgreementViewSetList:
    def test_return_agreements_only_from_agent_organization(
        self,
        app: DjangoTestApp,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        different_organization = OrganizationFactory()
        use_case = ProjectFactory(datasets=[dataset])
        AgreementFactory(project=use_case, assigner=different_organization, status=AgreementStatuses.SIGNED)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {"_data": []}

    def test_return_empty_if_agreement_does_not_exist(self, app: DjangoTestApp, valid_token: str, agreement_url: str):
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {"_data": []}

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
    def test_do_not_return_agreements_with_incorrect_status(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        incorrect_status: AgreementStatuses,
        dataset: Dataset,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        AgreementFactory(project=use_case, assigner=organization, status=incorrect_status)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {"_data": []}

    def test_do_not_return_agreements_unrelated_to_agent_service(
        self, app: DjangoTestApp, organization: Organization, valid_token: str, agreement_url: str
    ):
        dataset = DatasetFactory(organization=organization)
        use_case = ProjectFactory(datasets=[dataset])
        AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {"_data": []}

    @pytest.mark.parametrize("correct_status", [AgreementStatuses.SIGNED, AgreementStatuses.ACTIVE])
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        correct_status: AgreementStatuses,
        dataset: Dataset,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=correct_status)
        agreement_file = AgreementFileFactory(agreement=agreement)
        use_case_client = UseCaseClientFactory(use_case=use_case)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "_type": "datasets/gov/vssa/ror/dcat/Agreement",
                    "_id": str(agreement.uuid),
                    "_revision": "",
                    "_txn": "",
                    "_created": agreement.created_at.astimezone(timezone).isoformat(),
                    "_updated": agreement.updated_at.astimezone(timezone).isoformat(),
                    "@context": "",
                    "agreement_file_url": reverse(
                        "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file.uuid}
                    ),
                    "agreement_scopes": [
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                    ],
                    "clients": [
                        {
                            # TODO: Fix this in https://github.com/atviriduomenys/katalogas/issues/2287.
                            #  Should be: datasets/gov/vssa/isris/dcat/Client
                            "_type": "",
                            "_id": str(use_case_client.uuid),
                            "_revision": "",
                            "_txn": "",
                            "_created": use_case_client.created_at.astimezone(timezone).isoformat(),
                            "_updated": use_case_client.updated_at.astimezone(timezone).isoformat(),
                            "@context": "",
                        }
                    ],
                }
            ]
        }

    def test_success_when_dataset_is_agent_service_child(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        child_dataset = DatasetFactory(organization=organization)
        child_dataset.move(dataset, pos="sorted-child")
        use_case = ProjectFactory(datasets=[child_dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement_file = AgreementFileFactory(agreement=agreement)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "_type": "datasets/gov/vssa/ror/dcat/Agreement",
                    "_id": str(agreement.uuid),
                    "_revision": "",
                    "_txn": "",
                    "_created": agreement.created_at.astimezone(timezone).isoformat(),
                    "_updated": agreement.updated_at.astimezone(timezone).isoformat(),
                    "@context": "",
                    "agreement_file_url": reverse(
                        "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file.uuid}
                    ),
                    "agreement_scopes": [
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                    ],
                    "clients": [],
                }
            ]
        }

    def test_400_when_given_dataset_uuid_is_not_related_to_agent_service(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        non_existig_dataset_uuid = str(uuid4())
        use_case = ProjectFactory(datasets=[dataset])
        AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        response = app.get(
            f"{agreement_url}?datasets._id={non_existig_dataset_uuid}",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json["message"] == f"datasets._id values: {non_existig_dataset_uuid} are invalid."

    def test_filter_dataset_by_dataset_uuid(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        child_dataset = DatasetFactory(organization=organization)
        child_dataset.move(dataset, pos="sorted-child")

        use_case = ProjectFactory(datasets=[dataset])
        use_case2 = ProjectFactory(datasets=[child_dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement2 = AgreementFactory(project=use_case2, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement_file = AgreementFileFactory(agreement=agreement)
        AgreementFileFactory(agreement=agreement2)

        response = app.get(
            f"{agreement_url}?datasets._id={dataset.uuid}",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "_type": "datasets/gov/vssa/ror/dcat/Agreement",
                    "_id": str(agreement.uuid),
                    "_revision": "",
                    "_txn": "",
                    "_created": agreement.created_at.astimezone(timezone).isoformat(),
                    "_updated": agreement.updated_at.astimezone(timezone).isoformat(),
                    "@context": "",
                    "agreement_file_url": reverse(
                        "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file.uuid}
                    ),
                    "agreement_scopes": [
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                    ],
                    "clients": [],
                }
            ]
        }

    def test_filter_dataset_by_multiple_dataset_uuids(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        child_dataset = DatasetFactory(organization=organization)
        child_dataset2 = DatasetFactory(organization=organization)
        child_dataset.move(dataset, pos="sorted-child")
        child_dataset.refresh_from_db()
        child_dataset2.move(child_dataset, pos="sorted-child")
        child_dataset2.refresh_from_db()

        use_case = ProjectFactory(datasets=[dataset])
        use_case2 = ProjectFactory(datasets=[child_dataset])
        use_case3 = ProjectFactory(datasets=[child_dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement2 = AgreementFactory(project=use_case2, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement3 = AgreementFactory(project=use_case3, assigner=organization, status=AgreementStatuses.SIGNED)
        AgreementFileFactory(agreement=agreement)
        agreement_file2 = AgreementFileFactory(agreement=agreement2)
        agreement_file3 = AgreementFileFactory(agreement=agreement3)

        response = app.get(
            f"{agreement_url}?datasets._id={child_dataset.uuid}&datasets._id={child_dataset2.uuid}",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "_type": "datasets/gov/vssa/ror/dcat/Agreement",
                    "_id": str(agreement3.uuid),
                    "_revision": "",
                    "_txn": "",
                    "_created": agreement3.created_at.astimezone(timezone).isoformat(),
                    "_updated": agreement3.updated_at.astimezone(timezone).isoformat(),
                    "@context": "",
                    "agreement_file_url": reverse(
                        "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file3.uuid}
                    ),
                    "agreement_scopes": [
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                    ],
                    "clients": [],
                },
                {
                    "_type": "datasets/gov/vssa/ror/dcat/Agreement",
                    "_id": str(agreement2.uuid),
                    "_revision": "",
                    "_txn": "",
                    "_created": agreement2.created_at.astimezone(timezone).isoformat(),
                    "_updated": agreement2.updated_at.astimezone(timezone).isoformat(),
                    "@context": "",
                    "agreement_file_url": reverse(
                        "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file2.uuid}
                    ),
                    "agreement_scopes": [
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                    ],
                    "clients": [],
                },
            ]
        }

    def test_returns_latest_agreement_adoc_file(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        AgreementFileFactory(agreement=agreement)
        agreement_file2 = AgreementFileFactory(agreement=agreement)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json["_data"][0]["agreement_file_url"] == (
            reverse("uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file2.uuid})
        )

    def test_400_if_agreement_file_scopes_cannot_be_extracted(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement_file = AgreementFileFactory(agreement=agreement)

        with patch(
            "vitrina.uapi.views.agreement_views.extract_elements_from_adoc", side_effect=InvalidAdocError("Test error")
        ):
            response = app.get(
                agreement_url,
                extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
                expect_errors=True,
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json["message"] == (
            f"Scopes cannot be extracted from Agreement file (_id={agreement_file.uuid}). Error: Test error"
        )

    def test_400_if_agreement_adoc_does_not_exist(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        response = app.get(
            agreement_url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json["message"] == (f"Agreement adoc file does not exist for agreement (_id={agreement.uuid})")

    def test_returns_paginated_response(
        self,
        app: DjangoTestApp,
        organization: Organization,
        valid_token: str,
        agreement_url: str,
        dataset: Dataset,
    ):
        use_case = ProjectFactory(datasets=[dataset])
        agreement1 = AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        agreement_file1 = AgreementFileFactory(agreement=agreement1)
        AgreementFactory(project=use_case, assigner=organization, status=AgreementStatuses.SIGNED)
        response = app.get(
            f"{agreement_url}?_limit=1&_sort=_created",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "_type": "datasets/gov/vssa/ror/dcat/Agreement",
                    "_id": str(agreement1.uuid),
                    "_revision": "",
                    "_txn": "",
                    "_created": agreement1.created_at.astimezone(timezone).isoformat(),
                    "_updated": agreement1.updated_at.astimezone(timezone).isoformat(),
                    "@context": "",
                    "agreement_file_url": reverse(
                        "uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_file1.uuid}
                    ),
                    "agreement_scopes": [
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
                        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
                    ],
                    "clients": [],
                }
            ],
            "_next": UAPIPagination()._encode_uapi_urlsafe_base64(f'["{str(agreement1.created_at)}"]'),
        }
