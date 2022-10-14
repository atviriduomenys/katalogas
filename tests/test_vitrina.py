import pytest

from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory


@pytest.mark.django_db
def test_home(app: DjangoTestApp):
    ProjectFactory()

    org = OrganizationFactory()
    dataset = DatasetFactory.build(organization=org)
    dataset.set_current_language(settings.LANGUAGE_CODE)
    dataset.title = 'test'
    dataset.save()

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
