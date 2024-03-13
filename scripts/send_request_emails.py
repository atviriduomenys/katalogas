import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from datetime import timedelta
from typer import run
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from vitrina.helpers import email
from vitrina.tasks.services import get_holidays, get_past_work_date
from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request
from vitrina.orgs.models import Representative


def main():
    now = timezone.now().date()
    holidays = get_holidays(
        date_from=(now - timedelta(days=30)),
        date_to=now
    )
    date_5 = get_past_work_date(5, holidays)
    date_10 = get_past_work_date(10, holidays)
    domain = Site.objects.get_current().domain

    # For Requests that have related Datasets
    for request in Request.objects.filter(
        Q(status=Request.CREATED) &
        (Q(created__date=date_5) | Q(created__date=date_10)) &
        Q(requestobject__isnull=False)
    ).distinct():
        emails = []

        if rel_objects := request.requestobject_set.filter(
            content_type=ContentType.objects.get_for_model(Dataset)
        ):
            for obj in rel_objects:
                dataset = obj.content_object

                if request.created.date() == date_5:
                    coordinator_emails = Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(dataset.organization),
                        object_id=dataset.organization.pk,
                        role=Representative.COORDINATOR
                    ).values_list('email', flat=True)
                else:
                    parent_organization = dataset.organization.get_parent()

                    if not parent_organization:
                        parent_organization = dataset.organization

                    coordinator_emails = Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(parent_organization),
                        object_id=parent_organization.pk,
                        role=Representative.COORDINATOR
                    ).values_list('email', flat=True)

                emails.extend(list(coordinator_emails))

        if emails:
            email(
                emails,
                'request-late',
                'vitrina/emails/request_late_response.md',
                {
                    'request': request.title,
                    'link': "https://" + domain + request.get_absolute_url()
                }
            )

    # For Requests that don't have related Datasets, but have related RequestAssignment
    for request in Request.objects.filter(
        Q(status=Request.CREATED) &
        Q(requestassignment__isnull=False) &
        Q(requestobject__isnull=True) &
        (Q(requestassignment__created__date=date_5) | Q(requestassignment__created__date=date_10))
    ).distinct():
        emails = []

        if assignments := request.requestassignment_set.filter(
            Q(created__date=date_5) | Q(created__date=date_10)
        ):
            for assignment in assignments:
                organization = assignment.organization

                if assignment.created.date() == date_5:
                    coordinator_emails = Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(organization),
                        object_id=organization.pk,
                        role=Representative.COORDINATOR
                    ).values_list('email', flat=True)
                else:
                    parent_organization = organization.get_parent()

                    if not parent_organization:
                        parent_organization = organization

                    coordinator_emails = Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(parent_organization),
                        object_id=parent_organization.pk,
                        role=Representative.COORDINATOR
                    ).values_list('email', flat=True)

                emails.extend(list(coordinator_emails))

        if emails:
            email(
                emails,
                'request-late',
                'vitrina/emails/request_late_response.md',
                {
                    'request': request.title,
                    'link': "https://" + domain + request.get_absolute_url()
                }
            )


if __name__ == '__main__':
    run(main)
