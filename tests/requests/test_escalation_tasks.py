import freezegun
import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from vitrina.requests.tasks.escalation import start_escalation_for_request

from vitrina.comments.factories import CommentFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import RequestEscalation, RequestObject
from vitrina.comments.models import Comment
from vitrina.requests.tasks.escalation import (
    has_response_since_last_escalation,
    get_recipients_for_level,
    get_dataset_managers,
    get_organization_coordinators_emails,
    get_organization_email,
    escalate_to_next_level,
    schedule_escalation_check,
)
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory


@pytest.fixture
def organization():
    return OrganizationFactory()


@pytest.fixture
def dataset(organization):
    return DatasetFactory(organization=organization)


@pytest.fixture
def request_obj(dataset):
    request = RequestFactory(dataset=dataset)

    RequestObject.objects.create(
        request=request, content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk
    )

    return request


@pytest.fixture
def escalation(request_obj):
    return RequestEscalation.objects.create(
        request=request_obj,
        last_escalation_sent=timezone.now(),
        recipients_at_current_level=["editor1@example.com", "editor2@example.com"],
    )


@pytest.mark.django_db
class TestHasResponseSinceLastEscalation:
    def test_no_response(self, escalation):
        assert has_response_since_last_escalation(escalation) is False

    def test_status_comment_from_recipient(self, escalation):
        user = UserFactory(email="editor1@example.com")

        content_type = ContentType.objects.get_for_model(escalation.request)
        CommentFactory(
            content_type=content_type,
            object_id=escalation.request.pk,
            type=Comment.STATUS,
            user=user,
        )

        assert has_response_since_last_escalation(escalation) is True

    def test_regular_comment_from_recipient(self, escalation):
        user = UserFactory(email="editor2@example.com")

        content_type = ContentType.objects.get_for_model(escalation.request)
        CommentFactory(
            content_type=content_type,
            object_id=escalation.request.pk,
            type=Comment.USER,
            user=user,
        )

        assert has_response_since_last_escalation(escalation) is True

    def test_comment_from_non_recipient(self, escalation):
        user = UserFactory()

        content_type = ContentType.objects.get_for_model(escalation.request)
        CommentFactory(
            content_type=content_type,
            object_id=escalation.request.pk,
            user=user,
        )

        assert has_response_since_last_escalation(escalation) is False

    def test_comment_before_escalation(self, escalation):
        user = UserFactory(email="editor1@example.com")

        old_time = escalation.last_escalation_sent - timedelta(hours=1)

        content_type = ContentType.objects.get_for_model(escalation.request)
        comment = CommentFactory(
            content_type=content_type,
            object_id=escalation.request.pk,
            user=user,
        )
        comment.created = old_time
        comment.save()

        assert has_response_since_last_escalation(escalation) is False


@pytest.mark.django_db
class TestGetDatasetEditorsEmails:
    def test_get_editors_for_dataset(self, request_obj, dataset):
        dataset_ct = ContentType.objects.get_for_model(dataset)

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor1@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor2@example.com",
            role=Representative.RESOURCE_MANAGER,
        )

        emails = get_dataset_managers(request_obj)

        assert len(emails) == 2
        assert "editor1@example.com" in emails
        assert "editor2@example.com" in emails

    def test_exclude_coordinators(self, request_obj, dataset):
        dataset_ct = ContentType.objects.get_for_model(dataset)

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="coord@example.com",
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        emails = get_dataset_managers(request_obj)

        assert len(emails) == 1
        assert "editor@example.com" in emails
        assert "coord@example.com" not in emails

    def test_exclude_deleted_representatives(self, request_obj, dataset):
        dataset_ct = ContentType.objects.get_for_model(dataset)

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="deleted@example.com",
            role=Representative.OPEN_DATA_MANAGER,
            deleted=True,
        )

        emails = get_dataset_managers(request_obj)

        assert len(emails) == 0


@pytest.mark.django_db
class TestGetOrganizationCoordinatorsEmails:
    def test_get_coordinators_for_organization(self, request_obj, organization):
        org_ct = ContentType.objects.get_for_model(organization)

        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="coord1@example.com",
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="coord2@example.com",
            role=Representative.RESOURCE_COORDINATOR,
        )

        emails = get_organization_coordinators_emails(request_obj)

        assert len(emails) == 2
        assert "coord1@example.com" in emails
        assert "coord2@example.com" in emails

    def test_exclude_managers(self, request_obj, organization):
        org_ct = ContentType.objects.get_for_model(organization)

        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="coord@example.com",
            role=Representative.RESOURCE_COORDINATOR,
        )

        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="manager@example.com",
            role=Representative.RESOURCE_MANAGER,
        )

        emails = get_organization_coordinators_emails(request_obj)

        assert len(emails) == 1
        assert "coord@example.com" in emails
        assert "manager@example.com" not in emails


@pytest.mark.django_db
class TestGetOrganizationEmail:
    def test_get_organization_email(self, request_obj, organization):
        emails = get_organization_email(request_obj)

        assert len(emails) == 1
        assert organization.email in emails

    def test_no_organization_email(self, request_obj, organization):
        organization.email = None
        organization.save()

        emails = get_organization_email(request_obj)

        assert len(emails) == 0


@pytest.mark.django_db
class TestGetRecipientsForLevel:
    def test_level_manager(self, escalation, dataset):
        dataset_ct = ContentType.objects.get_for_model(dataset)

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        escalation.escalation_level = RequestEscalation.LEVEL_MANAGER

        recipients = get_recipients_for_level(escalation)

        assert "editor@example.com" in recipients

    def test_level_coordinator(self, escalation, organization):
        org_ct = ContentType.objects.get_for_model(organization)

        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="coord@example.com",
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        escalation.escalation_level = RequestEscalation.LEVEL_COORDINATOR

        recipients = get_recipients_for_level(escalation)

        assert "coord@example.com" in recipients

    def test_level_organization(self, escalation, organization):
        escalation.escalation_level = RequestEscalation.LEVEL_ORGANIZATION

        recipients = get_recipients_for_level(escalation)

        assert organization.email in recipients


@pytest.mark.django_db
class TestEscalateToNextLevel:
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_escalate_from_editors_to_coordinators(self, mock_schedule, mock_send_emails, escalation, organization):
        org_ct = ContentType.objects.get_for_model(organization)

        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="coord@example.com",
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        escalation.escalation_level = RequestEscalation.LEVEL_MANAGER
        escalation.save()

        escalate_to_next_level(escalation)

        escalation.refresh_from_db()

        assert escalation.escalation_level == RequestEscalation.LEVEL_COORDINATOR
        assert "coord@example.com" in escalation.recipients_at_current_level
        assert mock_send_emails.called
        assert mock_schedule.called

    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    def test_escalate_at_max_level(self, mock_send_emails, escalation):
        escalation.escalation_level = RequestEscalation.LEVEL_ORGANIZATION
        escalation.save()

        escalate_to_next_level(escalation)

        escalation.refresh_from_db()

        assert escalation.is_active is False
        assert escalation.stopped_reason == RequestEscalation.STOP_REASON_MAX_LEVEL

    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")  # Add this
    def test_escalate_skips_level_with_no_recipients(self, mock_schedule, mock_send_emails, escalation, organization):
        # No coordinators set up, should skip to organization level
        escalation.escalation_level = RequestEscalation.LEVEL_MANAGER
        escalation.save()

        escalate_to_next_level(escalation)

        escalation.refresh_from_db()

        # Should skip coordinators and go to organization
        assert escalation.escalation_level == RequestEscalation.LEVEL_ORGANIZATION
        assert organization.email in escalation.recipients_at_current_level


@pytest.mark.django_db
class TestScheduleEscalationCheck:
    def test_escalation_not_found(self):
        result = schedule_escalation_check(99999)
        assert "not found" in result

    def test_escalation_already_inactive(self, escalation):
        escalation.stop_escalation(RequestEscalation.STOP_REASON_MANUAL)

        result = schedule_escalation_check(escalation.id)

        assert "no longer active" in result

    @patch("vitrina.requests.tasks.escalation.has_response_since_last_escalation")
    def test_response_received(self, mock_has_response, escalation):
        mock_has_response.return_value = True

        result = schedule_escalation_check(escalation.id)

        escalation.refresh_from_db()

        assert "Response received" in result
        assert escalation.is_active is False
        assert escalation.stopped_reason == RequestEscalation.STOP_REASON_RESPONDED

    @patch("vitrina.requests.tasks.escalation.escalate_to_next_level")
    @patch("vitrina.requests.tasks.escalation.has_response_since_last_escalation")
    def test_no_response_escalates(self, mock_has_response, mock_escalate, escalation):
        mock_has_response.return_value = False

        result = schedule_escalation_check(escalation.id)

        assert mock_escalate.called
        assert "Escalated" in result


@pytest.mark.django_db
class TestEscalationPipelineFunctional:
    @freezegun.freeze_time("2025-11-18 10:00:00")  # Monday
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_request_creation_automatically_starts_escalation(
        self, mock_schedule, mock_send_emails, organization, dataset
    ):
        dataset_ct = ContentType.objects.get_for_model(dataset)
        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        request_obj = RequestFactory(dataset=dataset)
        RequestObject.objects.create(request=request_obj, content_type=dataset_ct, object_id=dataset.pk)

        escalation = start_escalation_for_request(request_obj)

        assert escalation is not None
        assert escalation.request == request_obj
        assert escalation.escalation_level == RequestEscalation.LEVEL_MANAGER
        assert escalation.is_active is True
        assert "editor@example.com" in escalation.recipients_at_current_level

        assert mock_send_emails.called
        assert mock_schedule.called

    @freezegun.freeze_time("2025-11-18 10:00:00")  # Monday
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_request_without_editors_skips_escalation(self, mock_schedule, mock_send_emails, organization, dataset):
        request_obj = RequestFactory(dataset=dataset)
        dataset_ct = ContentType.objects.get_for_model(dataset)
        RequestObject.objects.create(request=request_obj, content_type=dataset_ct, object_id=dataset.pk)

        escalation = start_escalation_for_request(request_obj)

        assert escalation is None
        assert not mock_send_emails.called
        assert not mock_schedule.called

    @freezegun.freeze_time("2025-11-18 10:00:00")  # Monday
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_full_escalation_through_all_levels(self, mock_schedule, mock_send_emails, organization, dataset):
        """
        Timeline:
        - Day 0 (Mon): Request created, editors notified
        - Day 5 (Mon): No response, escalate to coordinators
        - Day 10 (Mon): No response, escalate to organization
        - Day 15 (Mon): At max level, stops
        """
        dataset_ct = ContentType.objects.get_for_model(dataset)
        org_ct = ContentType.objects.get_for_model(organization)

        # Level 0: Editors
        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        # Level 1: Coordinators
        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="coordinator@example.com",
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        # Level 2: Organization (has email from fixture)

        # Day 0: Create request and start escalation
        request_obj = RequestFactory(dataset=dataset)
        RequestObject.objects.create(request=request_obj, content_type=dataset_ct, object_id=dataset.pk)

        escalation = start_escalation_for_request(request_obj)

        # Verify initial state
        assert escalation.escalation_level == RequestEscalation.LEVEL_MANAGER
        assert escalation.is_active is True

        # Day 5: No response, escalate to coordinators
        with freezegun.freeze_time("2025-11-25 10:00:00"):
            schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            assert escalation.escalation_level == RequestEscalation.LEVEL_COORDINATOR
            assert escalation.is_active is True
            assert "coordinator@example.com" in escalation.recipients_at_current_level

        # Day 10: No response, escalate to organization
        with freezegun.freeze_time("2025-12-02 10:00:00"):
            schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            assert escalation.escalation_level == RequestEscalation.LEVEL_ORGANIZATION
            assert escalation.is_active is True
            assert organization.email in escalation.recipients_at_current_level

        # Day 15: At max level, stops
        with freezegun.freeze_time("2025-12-16 10:00:00"):
            schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            assert escalation.escalation_level == RequestEscalation.LEVEL_ORGANIZATION
            assert escalation.is_active is False
            assert escalation.stopped_reason == RequestEscalation.STOP_REASON_MAX_LEVEL

    @freezegun.freeze_time("2025-11-18 10:00:00")  # Monday
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_editor_comment_stops_escalation(self, mock_schedule, mock_send_emails, organization, dataset):
        """
        Timeline:
        - Day 0: Request created, editor notified
        - Day 3: Editor comments on request
        - Day 5: Check runs, sees editor responded, stops escalation
        """
        dataset_ct = ContentType.objects.get_for_model(dataset)
        editor_user = UserFactory(email="editor@example.com")

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            user=editor_user,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        # Day 0: Create request
        request_obj = RequestFactory(dataset=dataset)
        RequestObject.objects.create(request=request_obj, content_type=dataset_ct, object_id=dataset.pk)

        escalation = start_escalation_for_request(request_obj)

        assert escalation.is_active is True

        # Day 3: Editor comments
        with freezegun.freeze_time("2025-11-21 14:00:00"):
            content_type = ContentType.objects.get_for_model(request_obj)
            CommentFactory(
                content_type=content_type,
                object_id=request_obj.pk,
                user=editor_user,
                type=Comment.USER,
                body="Working on this",
            )

        # Day 5: Escalation check runs
        with freezegun.freeze_time("2025-11-25 10:00:00"):
            schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            # Should stop - editor responded
            assert escalation.is_active is False
            assert escalation.stopped_reason == RequestEscalation.STOP_REASON_RESPONDED
            assert escalation.escalation_level == RequestEscalation.LEVEL_MANAGER

    @freezegun.freeze_time("2025-11-18 10:00:00")  # Monday
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_coordinator_response_after_escalation_stops_it(
        self, mock_schedule, mock_send_emails, organization, dataset
    ):
        """
        Timeline:
        - Day 0: Editors notified
        - Day 5: Escalate to coordinators
        - Day 7: Coordinator changes status
        - Day 10: Check runs, sees coordinator responded, stops
        """
        dataset_ct = ContentType.objects.get_for_model(dataset)
        org_ct = ContentType.objects.get_for_model(organization)

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        coordinator_user = UserFactory(email="coordinator@example.com")
        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            user=coordinator_user,
            email="coordinator@example.com",
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        # Day 0: Create request
        request_obj = RequestFactory(dataset=dataset)
        RequestObject.objects.create(request=request_obj, content_type=dataset_ct, object_id=dataset.pk)

        escalation = start_escalation_for_request(request_obj)

        # Day 5: Escalate to coordinators
        with freezegun.freeze_time("2025-11-25 10:00:00"):
            schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            assert escalation.escalation_level == RequestEscalation.LEVEL_COORDINATOR
            assert escalation.is_active is True

        # Day 7: Coordinator responds with status change
        with freezegun.freeze_time("2025-11-27 15:00:00"):
            content_type = ContentType.objects.get_for_model(request_obj)
            CommentFactory(
                content_type=content_type,
                object_id=request_obj.pk,
                user=coordinator_user,
                type=Comment.STATUS,
                body="Approved",
            )

        # Day 10: Check runs
        with freezegun.freeze_time("2025-12-02 10:00:00"):
            schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            # Should stop - coordinator responded
            assert escalation.is_active is False
            assert escalation.stopped_reason == RequestEscalation.STOP_REASON_RESPONDED
            assert escalation.escalation_level == RequestEscalation.LEVEL_COORDINATOR

    @freezegun.freeze_time("2025-11-18 10:00:00")  # Monday
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_non_recipient_comment_does_not_stop_escalation(
        self, mock_schedule, mock_send_emails, organization, dataset
    ):
        """
        Timeline:
        - Day 0: Editors notified
        - Day 3: Random user comments
        - Day 5: Escalation continues to coordinators (random comment ignored)
        """
        # Setup representatives
        dataset_ct = ContentType.objects.get_for_model(dataset)
        org_ct = ContentType.objects.get_for_model(organization)

        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        RepresentativeFactory(
            content_type=org_ct,
            object_id=organization.pk,
            email="coordinator@example.com",
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        # Day 0: Create request
        request_obj = RequestFactory(dataset=dataset)
        RequestObject.objects.create(request=request_obj, content_type=dataset_ct, object_id=dataset.pk)

        escalation = start_escalation_for_request(request_obj)

        # Day 3: Random user comments (not the notified editor)
        with freezegun.freeze_time("2025-11-21 14:00:00"):
            random_user = UserFactory(email="random@example.com")
            content_type = ContentType.objects.get_for_model(request_obj)
            CommentFactory(
                content_type=content_type,
                object_id=request_obj.pk,
                user=random_user,
                type=Comment.USER,
                body="Just a question",
            )

        # Day 5: Escalation check runs
        with freezegun.freeze_time("2025-11-25 10:00:00"):
            schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            # Should escalate - random comment doesn't count
            assert escalation.is_active is True
            assert escalation.escalation_level == RequestEscalation.LEVEL_COORDINATOR
            assert "coordinator@example.com" in escalation.recipients_at_current_level

    @freezegun.freeze_time("2025-11-18 10:00:00")  # Monday
    @patch("vitrina.requests.tasks.escalation.send_escalation_emails")
    @patch("vitrina.requests.tasks.escalation.schedule_escalation_check.apply_async")
    def test_manual_escalation_stop(self, mock_schedule, mock_send_emails, organization, dataset):
        """
        Timeline:
        - Day 0: Request created, editor notified
        - Day 3: Admin manually stops escalation
        - Day 5: Check runs, but escalation is inactive
        """
        dataset_ct = ContentType.objects.get_for_model(dataset)
        RepresentativeFactory(
            content_type=dataset_ct,
            object_id=dataset.pk,
            email="editor@example.com",
            role=Representative.OPEN_DATA_MANAGER,
        )

        # Day 0: Create request
        request_obj = RequestFactory(dataset=dataset)
        RequestObject.objects.create(request=request_obj, content_type=dataset_ct, object_id=dataset.pk)

        escalation = start_escalation_for_request(request_obj)

        # Day 3: Admin manually stops
        with freezegun.freeze_time("2025-11-21 11:00:00"):
            escalation.stop_escalation(RequestEscalation.STOP_REASON_MANUAL)

            assert escalation.is_active is False
            assert escalation.manually_stopped is True

        # Day 5: Scheduled check runs
        with freezegun.freeze_time("2025-11-25 10:00:00"):
            result = schedule_escalation_check(escalation.id)
            escalation.refresh_from_db()

            # Should not escalate
            assert "no longer active" in result
            assert escalation.escalation_level == RequestEscalation.LEVEL_MANAGER
