import pytest
import requests
from django.contrib.sites.models import Site

from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.sparql.tasks import sync_public_graph

FUSEKI_URL = "http://fuseki:3030/katalogas"


def create_dataset(title: str, access_rights: str) -> Dataset:
    return Dataset.objects.create(
        title=title,
        access_rights=access_rights,
        status=Dataset.HAS_DATA,
        is_public=True,
        organization=OrganizationFactory(),
    )


@pytest.mark.django_db
def test_sync_replaces_the_default_graph_with_public_datasets_only(settings, requests_mock):
    settings.FUSEKI_URL = FUSEKI_URL
    create_dataset("Viešas rinkinys", Dataset.PUBLIC)
    create_dataset("Riboto naudojimo rinkinys", Dataset.RESTRICTED)
    requests_mock.put(f"{FUSEKI_URL}/data")

    sync_public_graph()

    request = requests_mock.last_request
    assert request.method == "PUT"
    assert request.url == f"{FUSEKI_URL}/data?default"
    assert request.headers["Content-Type"] == "application/rdf+xml; charset=utf-8"
    body = request.body.decode()
    assert body.startswith("<?xml")
    assert f'xml:base="https://{Site.objects.get_current().domain}"' in body
    assert "Viešas rinkinys" in body
    assert "Riboto naudojimo rinkinys" not in body


@pytest.mark.django_db
def test_sync_fails_when_fuseki_rejects_the_graph(settings, requests_mock):
    settings.FUSEKI_URL = FUSEKI_URL
    requests_mock.put(f"{FUSEKI_URL}/data", status_code=500)

    with pytest.raises(requests.HTTPError):
        sync_public_graph()


@pytest.mark.django_db
def test_sync_does_nothing_without_fuseki_url(settings, requests_mock):
    settings.FUSEKI_URL = ""

    sync_public_graph()

    assert not requests_mock.called


@pytest.mark.django_db
def test_sync_is_scheduled_every_ten_minutes():
    from django_celery_beat.models import PeriodicTask

    task = PeriodicTask.objects.get(task="vitrina.sparql.tasks.sync_public_graph")

    assert task.enabled
    assert (task.interval.every, task.interval.period) == (10, "minutes")
