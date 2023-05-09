import pytest

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.projects.factories import ProjectFactory


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
