import requests
from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site

from vitrina.api.helpers import render_rdf
from vitrina.datasets.models import Dataset


@shared_task
def sync_public_graph() -> None:
    if not settings.FUSEKI_URL:
        return
    rdf = render_rdf(
        Dataset.edp_public.all(),
        only_link_rendered_datasets=True,
        context={"current_domain_full": f"https://{Site.objects.get_current().domain}"},
    )
    response = requests.put(
        f"{settings.FUSEKI_URL}/data?default",
        data=rdf.encode(),
        headers={"Content-Type": "application/rdf+xml; charset=utf-8"},
        timeout=300,
    )
    response.raise_for_status()
