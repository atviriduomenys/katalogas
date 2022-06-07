import pytest

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory


@pytest.mark.django_db
def test_home(app: DjangoTestApp):
    DatasetFactory()
    OrganizationFactory()
    ProjectFactory()

    resp = app.get('/')

    assert resp.status == '200 OK'
    assert resp.context['counts'] == {
        'dataset': 1,
        'organization': 1,
        'project': 1,
    }
    assert list(resp.html.find(id='counts').p.stripped_strings) == [
        '1 Datasets',
        '1 Organizations',
        '1 Projects',
    ]
