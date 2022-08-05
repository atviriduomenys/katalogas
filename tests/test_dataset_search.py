from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory


@pytest.mark.django_db
def test_dataset_search_view(app: DjangoTestApp):
    dataset1 = DatasetFactory(title="Duomenų rinkinys 1", title_en="Dataset 1", published=datetime(2022, 6, 1))
    dataset2 = DatasetFactory(title="Duomenų rinkinys 2", title_en="Dataset 2", published=datetime(2022, 8, 1))
    dataset3 = DatasetFactory(title="Duomenų rinkinys 3", title_en="Dataset 3", published=datetime(2022, 7, 1))

    # without query, ordered by published field
    resp = app.get(reverse('dataset-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 3
    assert resp.context['object_list'][0].pk == dataset2.pk
    assert resp.context['object_list'][1].pk == dataset3.pk
    assert resp.context['object_list'][2].pk == dataset1.pk

    # query that doesn't match any dataset
    resp = app.get("%s?q=%s" % (reverse('dataset-search-results'), "doesnt-match"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 0

    # query that matches one dataset
    resp = app.get("%s?q=%s" % (reverse('dataset-search-results'), "1"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset1.pk

    # query that matches all datasets with title
    resp = app.get("%s?q=%s" % (reverse('dataset-search-results'), "rinkinys"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 3

    # query that matches all datasets with english title
    resp = app.get("%s?q=%s" % (reverse('dataset-search-results'), "dataset"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 3
