from celery import shared_task
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from vitrina.requests.models import RequestEscalation
from vitrina.requests.utils import add_working_days
from vitrina.orgs.models import Organization, Representative
from vitrina.comments.models import Comment
from vitrina.helpers import email


ESCALATION_PERIOD_IN_WORKING_DAYS = 5


def start_escalation_for_request(request_obj):
    from django.utils import timezone

    if not (recipients := get_dataset_managers(request_obj)):
        return None

    escalation = RequestEscalation.objects.create(
        request=request_obj,
        escalation_level=RequestEscalation.LEVEL_MANAGER,
        last_escalation_sent=timezone.now(),
        recipients_at_current_level=recipients,
        is_active=True,
    )

    send_escalation_emails(escalation, recipients)

    next_check_time = add_working_days(timezone.now(), ESCALATION_PERIOD_IN_WORKING_DAYS)
    schedule_escalation_check.apply_async(args=[escalation.id], eta=next_check_time)

    return escalation


@shared_task
def schedule_escalation_check(escalation_id):
    try:
        escalation = RequestEscalation.objects.select_related("request").get(id=escalation_id)
    except RequestEscalation.DoesNotExist:
        return f"Escalation {escalation_id} not found"

    if not escalation.is_active:
        return f"Escalation {escalation_id} is no longer active"

    if has_response_since_last_escalation(escalation):
        escalation.stop_escalation(RequestEscalation.STOP_REASON_RESPONDED)
        return f"Response received for escalation {escalation_id}, stopping"

    if not escalation.can_escalate_further():
        escalation.stop_escalation(RequestEscalation.STOP_REASON_MAX_LEVEL)
        return f"Escalation {escalation_id} reached max level"

    escalate_to_next_level(escalation)

    return f"Escalated {escalation_id} to level {escalation.escalation_level}"


def has_response_since_last_escalation(escalation):
    request = escalation.request
    recipients = escalation.recipients_at_current_level
    last_sent = escalation.last_escalation_sent

    if not recipients:
        return False

    # Check for status changes by recipients
    content_type = ContentType.objects.get_for_model(request)
    status_comments = Comment.objects.filter(
        content_type=content_type,
        object_id=request.pk,
        type=Comment.STATUS,
        created__gt=last_sent,
        user__email__in=recipients,
    )

    if status_comments.exists():
        return True

    # Check for regular comments by recipients
    regular_comments = Comment.objects.filter(
        content_type=content_type,
        object_id=request.pk,
        type=Comment.USER,
        created__gt=last_sent,
        user__email__in=recipients,
    )

    return regular_comments.exists()


def escalate_to_next_level(escalation):
    escalation.escalation_level += 1

    if not (recipients := get_recipients_for_level(escalation)):
        if escalation.can_escalate_further():
            escalate_to_next_level(escalation)
        else:
            escalation.stop_escalation(RequestEscalation.STOP_REASON_MAX_LEVEL)
        return

    escalation.recipients_at_current_level = recipients
    escalation.last_escalation_sent = timezone.now()
    escalation.save()

    send_escalation_emails(escalation, recipients)

    if escalation.can_escalate_further():
        next_check_time = add_working_days(timezone.now(), ESCALATION_PERIOD_IN_WORKING_DAYS)
        schedule_escalation_check.apply_async(args=[escalation.id], eta=next_check_time)


def get_recipients_for_level(escalation):
    request = escalation.request
    level = escalation.escalation_level

    if level == RequestEscalation.LEVEL_MANAGER:
        return get_dataset_managers(request)

    if level == RequestEscalation.LEVEL_COORDINATOR:
        return get_organization_coordinators_emails(request)

    if level == RequestEscalation.LEVEL_ORGANIZATION:
        return get_organization_email(request)

    return []


def get_dataset_managers(request):
    request_objects = request.requestobject_set.all()

    emails = []
    for req_obj in request_objects:
        representatives = Representative.objects.filter(
            content_type_id=req_obj.content_type_id,
            object_id=req_obj.object_id,
            role=Representative.MANAGER,
            deleted__isnull=True,
        )

        for rep in representatives:
            if rep.email and rep.email not in emails:
                emails.append(rep.email)

    return emails


def get_organization_coordinators_emails(request):
    request_objects = request.requestobject_set.all()

    emails = []
    for req_obj in request_objects:
        if organization := get_organization_from_request_object(req_obj):
            org_content_type = ContentType.objects.get_for_model(Organization)

            coordinators = Representative.objects.filter(
                content_type=org_content_type,
                object_id=organization.id,
                role=Representative.COORDINATOR,
                deleted__isnull=True,
            )

            for coord in coordinators:
                if coord.email and coord.email not in emails:
                    emails.append(coord.email)

    return emails


def get_organization_email(request):
    request_objects = request.requestobject_set.all()

    emails = []
    for req_obj in request_objects:
        organization = get_organization_from_request_object(req_obj)

        if organization and organization.email:
            if organization.email not in emails:
                emails.append(organization.email)

    return emails


def get_organization_from_request_object(request_object):
    from vitrina.datasets.models import Dataset
    from vitrina.structure.models import Model

    obj = request_object.content_object

    if isinstance(obj, Dataset):
        return obj.organization

    elif isinstance(obj, Model):
        return obj.dataset.organization if obj.dataset else None

    return None


def send_escalation_emails(escalation, recipients):
    request = escalation.request
    level_name = escalation.get_level_display_name()

    email_context = {
        "request": request.title,
        "request_description": request.description,
        "request_link": f"{settings.SITE_URL}{request.get_absolute_url()}",
        "level": level_name,
        "days_since_created": (timezone.now() - request.created).days,
    }

    email(
        recipients,
        "request-escalation",
        "vitrina/emails/request_created_organization_sub.md",
        email_context,
    )
