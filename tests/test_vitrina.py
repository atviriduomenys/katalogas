import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
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
    }
    assert [list(elem.stripped_strings) for elem in resp.html.find_all(id="counts")] == [
        ['1', 'Rinkinių'],
        ['1', 'Organizacijų'],
        ['1', 'Panaudojimo atvejų'],
    ]


@pytest.mark.django_db
def test_request_create_link(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resp = app.get('/')
    resp = resp.click(linkid="request-create")
    assert resp.request.path == reverse('request-create')

