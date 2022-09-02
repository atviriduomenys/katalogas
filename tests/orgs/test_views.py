from datetime import datetime

from django.urls import reverse
from django_webtest import WebTest

from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization


class OrganizationTest(WebTest):
    def setUp(self):
        self.organization1 = OrganizationFactory(
            title="Organization 1",
            created=datetime(2022, 8, 22, 10, 30),
            jurisdiction="Jurisdiction1"
        )
        self.organization2 = OrganizationFactory(
            title="Organization 2",
            created=datetime(2022, 10, 22, 10, 30),
            jurisdiction="Jurisdiction2"
        )
        self.organization3 = OrganizationFactory(
            title="Organization 3",
            created=datetime(2022, 9, 22, 10, 30),
            jurisdiction="Jurisdiction2"
        )


class OrganizationSearchTest(OrganizationTest):
    def test_without_query(self):
        resp = self.app.get(reverse('organization-list'))
        self.assertEqual(
            list(resp.context['object_list']),
            [self.organization2, self.organization3, self.organization1]
        )

    def test_with_query_that_doesnt_match(self):
        resp = self.app.get("%s?q=%s" % (reverse('organization-list'), "doesnt-match"))
        self.assertEqual(len(resp.context['object_list']), 0)

    def test_with_query_that_matches_one(self):
        resp = self.app.get("%s?q=%s" % (reverse('organization-list'), "1"))
        self.assertEqual(list(resp.context['object_list']), [self.organization1])

    def test_with_query_that_matches_all(self):
        resp = self.app.get("%s?q=%s" % (reverse('organization-list'), "organization"))
        self.assertEqual(
            list(resp.context['object_list']),
            [self.organization2, self.organization3, self.organization1]
        )


class OrganizationFilterTest(OrganizationTest):
    def test_without_query(self):
        resp = self.app.get(reverse('organization-list'))
        self.assertEqual(
            list(resp.context['object_list']),
            [self.organization2, self.organization3, self.organization1]
        )
        self.assertIsNone(resp.context['selected_jurisdiction'])
        self.assertEqual(resp.context['jurisdictions'], [
            {
                'title': 'Jurisdiction1',
                'query': "?jurisdiction=Jurisdiction1",
                'count': 1
            },
            {
                'title': 'Jurisdiction2',
                'query': "?jurisdiction=Jurisdiction2",
                'count': 2
            }
        ])

    def test_with_jurisdiction(self):
        resp = self.app.get("%s?jurisdiction=Jurisdiction1" % reverse('organization-list'))
        self.assertEqual(list(resp.context['object_list']), [self.organization1])
        self.assertEqual(resp.context['selected_jurisdiction'], "Jurisdiction1")
        self.assertEqual(resp.context['jurisdictions'], [
            {
                'title': 'Jurisdiction1',
                'query': "?jurisdiction=Jurisdiction1",
                'count': 1
            },
            {
                'title': 'Jurisdiction2',
                'query': "?jurisdiction=Jurisdiction2",
                'count': 0
            }
        ])

    def test_with_other_jurisdiction(self):
        resp = self.app.get("%s?jurisdiction=Jurisdiction2" % reverse('organization-list'))
        self.assertEqual(list(resp.context['object_list']), [self.organization2, self.organization3])
        self.assertEqual(resp.context['selected_jurisdiction'], "Jurisdiction2")
        self.assertEqual(resp.context['jurisdictions'], [
            {
                'title': 'Jurisdiction1',
                'query': "?jurisdiction=Jurisdiction1",
                'count': 0
            },
            {
                'title': 'Jurisdiction2',
                'query': "?jurisdiction=Jurisdiction2",
                'count': 2
            }
        ])

    def test_with_non_existent_jurisdiction(self):
        resp = self.app.get("%s?jurisdiction=doesnotexist" % reverse('organization-list'))
        self.assertEqual(len(resp.context['object_list']), 0)
        self.assertEqual(resp.context['selected_jurisdiction'], "doesnotexist")
        self.assertEqual(resp.context['jurisdictions'], [
            {
                'title': 'Jurisdiction1',
                'query': "?jurisdiction=Jurisdiction1",
                'count': 0
            },
            {
                'title': 'Jurisdiction2',
                'query': "?jurisdiction=Jurisdiction2",
                'count': 0
            }
        ])

    def test_with_jurisdiction_and_title(self):
        resp = self.app.get("%s?q=1&jurisdiction=Jurisdiction1" % reverse('organization-list'))
        self.assertEqual(list(resp.context['object_list']), [self.organization1])
        self.assertEqual(resp.context['selected_jurisdiction'], "Jurisdiction1")
        self.assertEqual(resp.context['jurisdictions'], [
            {
                'title': 'Jurisdiction1',
                'query': "?q=1&jurisdiction=Jurisdiction1",
                'count': 1
            },
            {
                'title': 'Jurisdiction2',
                'query': "?q=1&jurisdiction=Jurisdiction2",
                'count': 0
            }
        ])

    def test_with_query_containing_special_characters(self):
        Organization.objects.all().delete()
        organization = OrganizationFactory(title="Organization \"<'>\\", jurisdiction="Jurisdiction\"<'>\\")
        resp = self.app.get("%s?q=\"<'>\\&jurisdiction=Jurisdiction\"<'>\\" % reverse('organization-list'))
        self.assertEqual(list(resp.context['object_list']), [organization])
        self.assertEqual(resp.context['selected_jurisdiction'], "Jurisdiction\"<'>\\")
        self.assertEqual(resp.context['jurisdictions'], [
            {
                'title': "Jurisdiction\"<'>\\",
                'query': "?q=\"<'>\\&jurisdiction=Jurisdiction\"<'>\\",
                'count': 1
            },
        ])
