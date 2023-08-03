import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.users.factories import UserFactory


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
        ['1', 'Organizacijos'],
        ['1', 'Duomenų rinkiniai'],
        ['1', 'Panaudojimo atvejai'],
        # ['0', 'Koordinatoriai'],
        # ['0', 'Tvarkytojai'],
        # ['0', 'Naudotojai'],
    ]


@pytest.mark.django_db
def test_request_create_link(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resp = app.get('/')
    resp = resp.click(linkid="request-create")
    assert resp.request.path == reverse('request-create')

