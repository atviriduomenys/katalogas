from datetime import datetime
from uuid import uuid4

import pytest
import pytz
from authlib.jose import RSAKey
from django.urls import reverse
from django_webtest import DjangoTestApp
from freezegun import freeze_time
from rest_framework import status
from django.conf import settings

from tests.uapi.conftest import _generate_test_token
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory


pytestmark = pytest.mark.django_db
timezone = pytz.timezone(settings.TIME_ZONE)


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
