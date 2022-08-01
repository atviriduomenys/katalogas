import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.orgs.models import Organization


@pytest.mark.django_db
def test_organization_search_view(app: DjangoTestApp):
    organization = Organization.objects.create(title="Organization 1", version=1)
    Organization.objects.create(title="Organization 2", version=1)
    Organization.objects.create(title="Organization 3", version=1)

    # without query
    resp = app.get(reverse('organization-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 3

    # query that doesn't match any organizations
    resp = app.get("%s?q=%s" % (reverse('organization-search-results'), "doesnt-match"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 0

    # query that matches one organization
    resp = app.get("%s?q=%s" % (reverse('organization-search-results'), "1"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == organization.pk

    # query that matches all organizations
    resp = app.get("%s?q=%s" % (reverse('organization-search-results'), "organization"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 3



