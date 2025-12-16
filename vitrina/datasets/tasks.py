from uuid import UUID
from celery import shared_task
from vitrina.services import fetch_page_title
from vitrina.classifiers.models import ApplicableLegislation


@shared_task
def update_applicable_legislation_description(legislation_id: UUID) -> None:
    legislation = ApplicableLegislation.objects.get(pk=legislation_id)
    if title := fetch_page_title(legislation.url):
        legislation.description = title
        legislation.save(update_fields=["description"])
