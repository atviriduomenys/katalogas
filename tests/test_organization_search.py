from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory


@pytest.fixture
def organizations():
    organization1 = OrganizationFactory(title="Organization 1", created=datetime(2022, 8, 22, 10, 30))
    organization2 = OrganizationFactory(title="Organization 2", created=datetime(2022, 10, 22, 10, 30))
    organization3 = OrganizationFactory(title="Organization 3", created=datetime(2022, 9, 22, 10, 30))
    return [organization1, organization2, organization3]


@pytest.mark.django_db
def test_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]


@pytest.mark.django_db
def test_with_query_that_doesnt_match(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "doesnt-match"))
    assert len(resp.context['object_list']) == 0


@pytest.mark.django_db
def test_with_query_that_matches_one(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "1"))
    assert list(resp.context['object_list']) == [organizations[0]]


@pytest.mark.django_db
def test_with_query_that_matches_all(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "organization"))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]



