from uuid import UUID
from celery import shared_task
from vitrina.services import fetch_page_title
from vitrina.classifiers.models import ApplicableLegislation


@shared_task
def update_applicable_legislation_description(legislation_ids: list[UUID]) -> None:
    legislations = ApplicableLegislation.objects.filter(pk__in=legislation_ids)
    for legislation in legislations:
        if title := fetch_page_title(legislation.url):
            legislation.description = title
            legislation.save(update_fields=["description", "updated_at"])
