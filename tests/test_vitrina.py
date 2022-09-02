from django.urls import reverse

from django_webtest import WebTest

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory


class HomeTest(WebTest):
    def setUp(self):
        DatasetFactory()
        OrganizationFactory()
        ProjectFactory()

    def test_home(self):
        resp = self.app.get(reverse('home'))
        self.assertEqual(resp.context['counts'], {
            'dataset': 1,
            'organization': 1,
            'project': 1,
        })
        self.assertEqual([list(elem.stripped_strings) for elem in resp.html.find_all(id="counts")], [
            ['1', 'Rinkinių'],
            ['1', 'Organizacijų'],
            ['1', 'Panaudojimo atvejų'],
        ])
