import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request


@pytest.mark.django_db
def test_request_create(csrf_exempt_django_app: DjangoTestApp):
    resp = csrf_exempt_django_app.post(reverse("request-create"), {
        'title': "Request",
        'description': "Description"
    })
    assert Request.objects.count() == 1
    assert resp.status_code == 302
    assert resp.url == reverse('request-detail', args=[Request.objects.first().pk])


@pytest.mark.django_db
def test_request_update(csrf_exempt_django_app: DjangoTestApp):
    request = RequestFactory()
    resp = csrf_exempt_django_app.post(reverse("request-update", args=[request.pk]), {
        'title': "Updated title",
        'description': "Updated description"
    })
    assert resp.status_code == 302
    assert resp.url == reverse('request-detail', args=[request.pk])
    assert Request.objects.first().title == "Updated title"
    assert Request.objects.first().description == "Updated description"


@pytest.mark.django_db
def test_request_detail_view(app: DjangoTestApp):
    dataset = DatasetFactory()
    request = RequestFactory(
        dataset_id=dataset.pk,
        is_existing=True,
        status="REJECTED",
        purpose="science,product",
        changes="format",
        format="csv, json, rdf",
        structure_data=(
            "data1,dictionary1,type1,notes1;"
            "data2,dictionary2,type2,notes2"
        )
    )

    resp = app.get(reverse('request-detail', args=[request.pk]))

    assert resp.context['status'] == "Atmestas"
    assert resp.context['purposes'] == ['science', 'product']
    assert resp.context['changes'] == ['format']
    assert resp.context['formats'] == ['csv', 'json', 'rdf']
    assert resp.context['like_count'] == 0
    assert not resp.context['liked']
    assert resp.context['structure'] == [
        {
            "data_title": 'data1',
            "dictionary_title": 'dictionary1',
            "data_type": 'type1',
            "data_notes": 'notes1',
        },
        {
            "data_title": 'data2',
            "dictionary_title": 'dictionary2',
            "data_type": 'type2',
            "data_notes": 'notes2',
        }
    ]
