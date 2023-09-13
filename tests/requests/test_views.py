from datetime import date, timedelta

import pytest
import pytz
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan
from vitrina.requests.factories import RequestFactory, RequestStructureFactory, RequestObjectFactory
from vitrina.requests.models import Request
from vitrina.users.factories import UserFactory, ManagerFactory
from vitrina.users.factories import UserFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.mark.django_db
def test_request_create(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    orgs = [OrganizationFactory(), OrganizationFactory()]
    app.set_user(user)
    form = app.get(reverse("request-create")).forms['request-form']
    form['title'] = "Request"
    form['description'] = "Description"
    resp = form.submit()
    added_request = Request.objects.filter(title="Request")
    assert added_request.count() == 1
    assert resp.status_code == 302
    assert resp.url == Request.objects.filter(title='Request').first().get_absolute_url()
    assert Version.objects.get_for_object(added_request.first()).count() == 1
    assert Version.objects.get_for_object(added_request.first()).first().revision.comment == Request.CREATED


@pytest.mark.django_db
def test_request_update_with_user_without_permission(app: DjangoTestApp):
    user = UserFactory()
    request = RequestFactory()
    request.save()

    app.set_user(user)
    resp = app.get(reverse("request-update", args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_request_update_with_permitted_user(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    request = RequestFactory(user=user)
    app.set_user(user)
    form = app.get(reverse("request-update", args=[request.pk])).forms['request-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()
    request.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == request.get_absolute_url()
    assert request.title == "Updated title"
    assert request.description == "Updated description"
    assert Version.objects.get_for_object(request).count() == 1
    assert Version.objects.get_for_object(request).first().revision.comment == Request.EDITED


@pytest.mark.django_db
def test_request_detail_view(app: DjangoTestApp):
    request = RequestFactory(
        is_existing=True,
        status="REJECTED",
        purpose="science,product",
        changes="format",
        format="csv, json, rdf",
    )
    structure1 = RequestStructureFactory(request_id=request.pk)
    structure2 = RequestStructureFactory(request_id=request.pk)

    resp = app.get(reverse('request-detail', args=[request.pk]))

    assert resp.context['status'] == "Atmestas"
    assert resp.context['purposes'] == ['science', 'product']
    assert resp.context['changes'] == ['format']
    assert resp.context['formats'] == ['csv', 'json', 'rdf']
    assert list(resp.context['structure']) == [structure1, structure2]


@pytest.mark.django_db
def test_request_history_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    request = RequestFactory()
    app.set_user(user)
    resp = app.get(reverse('request-history', args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_request_history_view_with_permission(app: DjangoTestApp):
    user = ManagerFactory(is_staff=True)
    orgs = [OrganizationFactory().pk, OrganizationFactory().pk]
    request = RequestFactory(user=user)
    request.organizations.add(user.organization)
    app.set_user(user)

    form = app.get(reverse("request-update", args=[request.pk])).forms['request-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit().follow()
    resp = resp.click(linkid="history-tab")
    assert resp.context['detail_url_name'] == 'request-detail'
    assert resp.context['history_url_name'] == 'request-history'
    assert len(resp.context['history']) == 1
    assert resp.context['history'][0]['action'] == "Redaguota"
    assert resp.context['history'][0]['user'] == user


@pytest.mark.django_db
def test_add_request_to_plan_with_non_representative(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    request = RequestFactory(user=user)

    resp = app.get(reverse('request-plans-include', args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_add_request_to_plan_with_representative(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    app.set_user(representative.user)
    request = RequestFactory(user=representative.user)
    plan = PlanFactory(
        deadline=(date.today() + timedelta(days=1))
    )

    form = app.get(reverse('request-plans-include', args=[request.pk])).forms['request-plan-form']
    form['plan'] = plan.pk
    resp = form.submit()

    assert resp.url == reverse('request-plans', args=[request.pk])
    assert request.planrequest_set.count() == 1
    assert request.planrequest_set.first().plan == plan


@pytest.mark.django_db
def test_add_request_to_plan_with_closed_request(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    request = RequestFactory(status=Request.REJECTED)

    resp = app.get(reverse('request-plans-include', args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_add_request_to_plan_title(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    request = RequestFactory()
    request.organizations.add(organization)

    form = app.get(reverse('request-plans-create', args=[request.pk])).forms['plan-form']
    form.submit()

    plan = Plan.objects.filter(planrequest__request=request)
    assert plan.count() == 1
    assert plan.first().title == "Duomenų rinkinio papildymas"


@pytest.mark.django_db
def test_add_request_to_plan_title_error(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    request_object = RequestObjectFactory(
        external_object_id="123",
        external_content_type="datasets/Model"
    )
    request_object.request.organizations.add(organization)

    form = app.get(reverse('request-plans-create', args=[request_object.request.pk])).forms['plan-form']
    form.submit()

    plan = Plan.objects.filter(planrequest__request=request_object.request)
    assert plan.count() == 1
    assert plan.first().title == "Klaidų duomenyse pataisymas"
