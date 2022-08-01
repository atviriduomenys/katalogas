import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory


@pytest.mark.django_db
def test_dataset_detail_view(app: DjangoTestApp):
    dataset = DatasetFactory()
    resp = app.get(reverse('dataset-detail', args=[dataset.slug]))

    # without tags
    assert len(resp.context['tags']) == 0
    assert resp.context['tags'] == ""

    # with tags
    dataset.tags = "tag-1, tag-2, tag-3"
    dataset.save()
    resp = app.get(reverse('dataset-detail', args=[dataset.slug]))
    assert resp.status == '200 OK'
    assert len(resp.context['tags']) == 3
    assert resp.context['tags'] == ['tag-1', 'tag-2', 'tag-3']

    # hardcoded values, will need to change with later tasks
    assert resp.context['subscription'] == []
    assert resp.context['views'] == -1
    assert resp.context['rating'] == 3.0

    # without status
    assert resp.context['status'] == ""

    # status HAS_DATA
    dataset.status = 'HAS_DATA'
    dataset.save()
    resp = app.get(reverse('dataset-detail', args=[dataset.slug]))
    assert resp.context['status'] == "Atvertas"

    # status INVENTORED
    dataset.status = 'INVENTORED'
    dataset.save()
    resp = app.get(reverse('dataset-detail', args=[dataset.slug]))
    assert resp.context['status'] == "Inventorintas"

    # status METADATA
    dataset.status = 'METADATA'
    dataset.save()
    resp = app.get(reverse('dataset-detail', args=[dataset.slug]))
    assert resp.context['status'] == "Parengti metaduomenys"

    # status PRIORITIZED
    dataset.status = 'PRIORITIZED'
    dataset.save()
    resp = app.get(reverse('dataset-detail', args=[dataset.slug]))
    assert resp.context['status'] == "Įvertinti prioritetai"

    # status FINANCING
    dataset.status = 'FINANCING'
    dataset.save()
    resp = app.get(reverse('dataset-detail', args=[dataset.slug]))
    assert resp.context['status'] == "Įvertintas finansavimas"

