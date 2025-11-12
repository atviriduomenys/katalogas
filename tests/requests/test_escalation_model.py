import pytest
from django.utils import timezone

from vitrina.requests.models import Request, RequestEscalation


@pytest.mark.django_db
class TestRequestEscalationModel:
    def test_create_escalation(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
        )

        assert escalation.escalation_level == RequestEscalation.LEVEL_EDITORS
        assert escalation.is_active is True
        assert escalation.manually_stopped is False
        assert escalation.stopped_at is None
        assert escalation.stopped_reason == ""
        assert escalation.recipients_at_current_level == []

    def test_one_to_one_relationship(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
        )

        with pytest.raises(Exception):
            RequestEscalation.objects.create(
                request=request,
                last_escalation_sent=timezone.now(),
            )

    def test_stop_escalation_responded(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
        )

        before_stop = timezone.now()
        escalation.stop_escalation(RequestEscalation.STOP_REASON_RESPONDED)

        assert escalation.is_active is False
        assert escalation.stopped_reason == RequestEscalation.STOP_REASON_RESPONDED
        assert escalation.manually_stopped is False
        assert escalation.stopped_at is not None
        assert escalation.stopped_at >= before_stop

    def test_stop_escalation_manual(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
        )

        escalation.stop_escalation(RequestEscalation.STOP_REASON_MANUAL)

        assert escalation.is_active is False
        assert escalation.stopped_reason == RequestEscalation.STOP_REASON_MANUAL
        assert escalation.manually_stopped is True  # Should be True for manual stops
        assert escalation.stopped_at is not None

    def test_stop_escalation_max_level(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            escalation_level=RequestEscalation.LEVEL_ORGANIZATION,
        )

        escalation.stop_escalation(RequestEscalation.STOP_REASON_MAX_LEVEL)

        assert escalation.is_active is False
        assert escalation.stopped_reason == RequestEscalation.STOP_REASON_MAX_LEVEL
        assert escalation.manually_stopped is False

    def test_can_escalate_further_at_editors_level(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            escalation_level=RequestEscalation.LEVEL_EDITORS,
        )

        assert escalation.can_escalate_further() is True

    def test_can_escalate_further_at_coordinators_level(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            escalation_level=RequestEscalation.LEVEL_COORDINATORS,
        )

        assert escalation.can_escalate_further() is True

    def test_can_escalate_further_at_organization_level(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            escalation_level=RequestEscalation.LEVEL_ORGANIZATION,
        )

        assert escalation.can_escalate_further() is False

    def test_get_level_display_name(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            escalation_level=RequestEscalation.LEVEL_COORDINATORS,
        )

        display_name = escalation.get_level_display_name()
        assert display_name == "Organizacijos koordinatorius"

    def test_recipients_tracking(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        recipients = ["editor1@example.com", "editor2@example.com"]

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            recipients_at_current_level=recipients,
        )

        assert escalation.recipients_at_current_level == recipients
        assert len(escalation.recipients_at_current_level) == 2

    def test_str_representation(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            escalation_level=RequestEscalation.LEVEL_EDITORS,
        )

        str_repr = str(escalation)
        assert f"#{request.pk}" in str_repr
        assert "0" in str_repr  # Level 0

    def test_escalation_progression(self):
        request = Request.objects.create(status=Request.CREATED, title="Test Request")

        escalation = RequestEscalation.objects.create(
            request=request,
            last_escalation_sent=timezone.now(),
            escalation_level=RequestEscalation.LEVEL_EDITORS,
        )

        # Simulate escalation progression
        assert escalation.can_escalate_further() is True

        escalation.escalation_level = RequestEscalation.LEVEL_COORDINATORS
        escalation.save()
        assert escalation.can_escalate_further() is True

        escalation.escalation_level = RequestEscalation.LEVEL_ORGANIZATION
        escalation.save()
        assert escalation.can_escalate_further() is False
