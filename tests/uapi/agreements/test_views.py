from datetime import datetime
from uuid import uuid4

import pytest
import pytz
from django_webtest import DjangoTestApp
from freezegun import freeze_time
from rest_framework import status
from django.conf import settings

from tests.uapi.conftest import build_reverse_uapi_url
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory

pytestmark = pytest.mark.django_db
timezone = pytz.timezone(settings.TIME_ZONE)


def test_sync_done_update_404_when_agreement_does_not_exist(
    app: DjangoTestApp, organization: Organization
) -> None:
    response = app.put(
        build_reverse_uapi_url(
            "agent-sync-done", organization, agreement_id=str(uuid4())
        ),
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_sync_done_update_404_when_organization_from_different_organization(
    app: DjangoTestApp,
    organization: Organization,
    project: Project,
) -> None:
    agreement = AgreementFactory(project=project, assigner=organization)
    different_organization = OrganizationFactory()

    response = app.put(
        build_reverse_uapi_url(
            "agent-sync-done", different_organization, agreement_id=agreement.pk
        ),
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_sync_done_update_404_when_agreement_sync_disabled(
    app: DjangoTestApp,
    organization: Organization,
    project: Project,
) -> None:
    agreement = AgreementFactory(
        project=project, assigner=organization, is_agent_sync_enabled=False
    )

    response = app.put(
        build_reverse_uapi_url(
            "agent-sync-done", organization, agreement_id=agreement.pk
        ),
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_sync_done_updates_last_sync_date_and_status_to_active(
    app: DjangoTestApp,
    organization: Organization,
    project: Project,
) -> None:
    agreement = AgreementFactory(
        project=project, assigner=organization, is_agent_sync_enabled=True
    )

    response = app.put(
        build_reverse_uapi_url(
            "agent-sync-done", organization, agreement_id=agreement.pk
        ),
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_200_OK
    agreement.refresh_from_db()
    assert agreement.last_sync_date
    assert agreement.status == AgreementStatuses.ACTIVE


def test_sync_done_does_not_update_agreement_updated_at(
    app: DjangoTestApp,
    organization: Organization,
    project: Project,
) -> None:
    creation_date = datetime(2024, 3, 3, 12, tzinfo=timezone)
    with freeze_time(creation_date):
        agreement = AgreementFactory(
            project=project, assigner=organization, is_agent_sync_enabled=True
        )

    with freeze_time(datetime(2024, 5, 5, 12, tzinfo=timezone)):
        response = app.put(
            build_reverse_uapi_url(
                "agent-sync-done", organization, agreement_id=agreement.pk
            ),
            expect_errors=True,
        )

    assert response.status_code == status.HTTP_200_OK
    agreement.refresh_from_db()
    assert agreement.updated_at == creation_date
