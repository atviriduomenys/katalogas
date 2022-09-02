from django.urls import reverse
from django_webtest import WebTest

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory


class OrganizationDetailTest(WebTest):
    def setUp(self):
        self.parent_organization = OrganizationFactory()
        self.organization = self.parent_organization.add_child(**OrganizationFactory.stub().__dict__)
        self.dataset = DatasetFactory(organization=self.organization)
        self.representative = RepresentativeFactory(organization=self.organization)

    def test_organization_detail_tab(self):
        resp = self.app.get(reverse('organization-detail', args=[self.organization.kind, self.organization.slug]))
        self.assertEqual(list(resp.context['ancestors']), [self.parent_organization])
        self.assertEqual(list(resp.html.find("li", class_="is-active").a.stripped_strings), ["Informacija"])

    def test_organization_members_tab(self):
        resp = self.app.get(reverse('organization-members', args=[self.organization.kind, self.organization.slug]))
        self.assertEqual(list(resp.context['members']), [self.representative])
        self.assertEqual(list(resp.html.find("li", class_="is-active").a.stripped_strings), ["Organizacijos nariai"])

    def test_organization_dataset_tab(self):
        resp = self.app.get(reverse('organization-datasets', args=[self.organization.kind, self.organization.slug]))
        assert list(resp.context['object_list']) == [self.dataset]
        assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Duomenų rinkiniai"]
