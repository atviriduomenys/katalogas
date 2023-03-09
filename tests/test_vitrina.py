import pytest
from datetime import datetime, date
import pytz

from django_webtest import DjangoTestApp
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory
from vitrina.projects.factories import ProjectFactory

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.mark.django_db
def test_home(app: DjangoTestApp):
    ProjectFactory()
    DatasetFactory()
    resp = app.get('/')

    assert resp.status == '200 OK'
    assert resp.context['counts'] == {
        'dataset': 1,
        'organization': 1,
        'project': 1,
        'coordinators': 0,
        'managers': 0,
        'users': 0
    }

    assert [
        list(elem.stripped_strings)
        for elem in resp.html.select('a.stats')
    ] == [
        ['1', 'Rinkinių'],
        ['1', 'Organizacijų'],
        ['1', 'Panaudojimo atvejų'],
        ['0', 'Koordinatoriai'],
        ['0', 'Tvarkytojai'],
        ['0', 'Naudotojai'],
    ]

@pytest.fixture
def search_datasets():
    dataset1 = DatasetFactory(slug='ds1', published=timezone.localize(datetime(2022, 6, 1)))
    dataset1.set_current_language('en')
    dataset1.title = 'Dataset 1'
    dataset1.save()
    dataset1.set_current_language('lt')
    dataset1.title = "Duomenų rinkinys vienas"
    dataset1.save()

    dataset2 = DatasetFactory(slug='ds2', published=timezone.localize(datetime(2022, 8, 1)))
    dataset2.set_current_language('en')
    dataset2.title = 'Dataset 2'
    dataset2.save()
    dataset2.set_current_language('lt')
    dataset2.title = "Duomenų rinkinys du\"<'>\\"
    dataset2.save()

    dataset3 = DatasetFactory(slug='ds3', published=timezone.localize(datetime(2022, 7, 1)))
    dataset3.set_current_language('en')
    dataset3.title = 'Dataset 3'
    dataset3.save()
    dataset3.set_current_language('lt')
    dataset3.title = "Duomenų rinkinys trys"
    dataset3.save()
    return [dataset1, dataset2, dataset3]

@pytest.mark.haystack
@pytest.mark.django_db
def test_empty_search_field(app: DjangoTestApp, search_datasets):
    form = app.get("/").forms['quick-search']
    resp = form.submit()
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]

@pytest.mark.haystack
@pytest.mark.django_db
def test_filled_search_field(app: DjangoTestApp, search_datasets):
    form = app.get("/").forms['quick-search']
    form['q'] = "trys"
    resp = form.submit()
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_datasets[2].pk]