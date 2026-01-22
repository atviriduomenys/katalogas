from datetime import date, timedelta
from unittest.mock import patch

import pytest
import pytz
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Representative
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan
from vitrina.requests.factories import (
    RequestFactory,
    RequestStructureFactory,
    RequestObjectFactory,
    RequestAssignmentFactory,
)
from vitrina.requests.models import Request, RequestObject
from vitrina.users.factories import UserFactory, ManagerFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.utils import RevisionComment, RevisionSource

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.mark.django_db
def test_request_create(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    url = reverse("request-create")
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="request-create",
        http_method="POST",
        path=url,
        args=(),
        kwargs={}
    )
    form = app.get(url).forms['request-form']
    form['title'] = "Request"
    form['description'] = "Description"
    resp = form.submit()
    added_request = Request.objects.filter(translations__title="Request")
    assert added_request.count() == 1
    assert resp.status_code == 302
    assert resp.url == Request.objects.filter(translations__title='Request').first().get_absolute_url()
    assert Version.objects.get_for_object(added_request.first()).count() == 1
    assert Version.objects.get_for_object(added_request.first()).first().revision.comment == revision_comment.to_json()


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
    url = reverse("request-update", args=[request.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="request-update",
        http_method="POST",
        path=url,
        args=(),
        kwargs={"pk": request.pk}
    )
    form = app.get(url).forms['request-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == request.get_absolute_url()
    updated_request = Request.objects.get(pk=request.pk)
    assert updated_request.title == "Updated title"
    assert updated_request.description == "Updated description"
    assert Version.objects.get_for_object(request).count() == 1
    assert Version.objects.get_for_object(request).first().revision.comment == revision_comment.to_json()


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
    request = RequestFactory(user=user)
    request.organizations.add(user.organization)
    app.set_user(user)

    url = reverse("request-update", args=[request.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="request-update",
        http_method="POST",
        path=url,
        args=(),
        kwargs={"pk": request.pk}
    )
    form = app.get(url).forms['request-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit().follow()
    resp = resp.click(linkid="history-tab")
    assert resp.context['detail_url_name'] == 'request-detail'
    assert resp.context['history_url_name'] == 'request-history'
    assert len(resp.context['history']) == 1
    history_action = resp.context['history'][0]['action']
    assert history_action["comment"] == f"{revision_comment.action}({revision_comment.kwargs})"
    assert resp.context['history'][0]['user'] == user


@pytest.mark.django_db
def test_add_request_to_plan_with_non_representative(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    request = RequestFactory(user=user)

    resp = app.get(reverse('request-plans-create', args=[request.pk]), expect_errors=True)
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
    request = RequestFactory(user=representative.user, status=Request.APPROVED)
    RequestAssignmentFactory(
        request=request,
        organization=organization
    )
    plan = PlanFactory(
        deadline=(date.today() + timedelta(days=1))
    )

    resp = app.get(reverse('request-plans-create', args=[request.pk]))
    form = resp.forms['request-plan-form']
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

    resp = app.get(reverse('request-plans-create', args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_add_request_to_plan_title(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    request = RequestFactory(status=Request.APPROVED)
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
    request_object.request.status = Request.APPROVED
    request_object.request.save()

    form = app.get(reverse('request-plans-create', args=[request_object.request.pk])).forms['plan-form']
    form.submit()

    plan = Plan.objects.filter(planrequest__request=request_object.request)
    assert plan.count() == 1
    assert plan.first().title == "Klaidų duomenyse pataisymas"


@pytest.mark.django_db
def test_request_orgs_view(app: DjangoTestApp):
    organization = OrganizationFactory()
    request = RequestFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    resp = app.get(reverse('request-organizations', args=[request.pk]))
    assert resp.html.find(id='display_date')


@pytest.mark.django_db
def test_request_orgs_view_delete_button_no_user(app: DjangoTestApp):
    request = RequestFactory()
    resp = app.get(reverse('request-organizations', args=[request.pk]))
    delete_button = resp.html.find(id='request-orgs-delete')
    assert delete_button is None


@pytest.mark.django_db
def test_request_orgs_view_click_delete_button_no_user(app: DjangoTestApp):
    request = RequestFactory()
    resp = app.get(reverse('request-organizations', args=[request.pk]))
    resp = resp.click(linkid='org-dataset-url')
    assert resp.url == reverse('request-organizations', args=[request.pk])


@pytest.mark.django_db
def test_request_orgs_view_click_delete_button_redirects_if_no_user(app: DjangoTestApp):
    request = RequestFactory()
    organization = OrganizationFactory()
    ra = RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    resp = app.get(reverse('request-orgs-delete', args=[ra.pk]))
    assert resp.url == reverse('request-organizations', args=[request.pk])


@pytest.mark.django_db
def test_request_orgs_view_click_delete_button_staff_user(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    request = RequestFactory()
    organization = OrganizationFactory()
    ra = RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    form = app.get(reverse('request-orgs-delete', args=[ra.pk])).forms['delete-form']
    resp = form.submit()
    assert resp.url == reverse('request-organizations', args=[request.pk])


@pytest.mark.django_db
def test_add_new_dataset_to_request_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    request = RequestFactory()
    organization = OrganizationFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    subclass = DCATResourceSubclassFactory()

    resp = app.get(reverse('request-datasets', args=[request.pk]))
    assert "add-new-dataset" not in resp.text
    resp = app.get(
        reverse('dataset-add', args=[organization.pk, subclass.pk]) + f"?next={reverse('request-datasets', args=[request.pk])}",
        expect_errors=True
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_add_new_dataset_to_request_with_representative_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(organization=organization)
    app.set_user(user)
    request = RequestFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    resp = app.get(reverse('request-datasets', args=[request.pk]))
    assert "add-new-dataset" in resp.text
    resp = resp.click(linkid="add-new-dataset")
    assert resp.request.path_qs == \
           reverse('resource-subclass-add', args=[organization.pk]) + f"?next={reverse('request-datasets', args=[request.pk])}"


@pytest.mark.django_db
def test_add_new_dataset_to_request_with_organization_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    organization2 = OrganizationFactory()
    user = UserFactory(organization=organization2)
    app.set_user(user)
    request = RequestFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    RepresentativeFactory(
        organization=organization2,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization2),
        object_id=organization2.pk
    )
    resp = app.get(reverse('request-datasets', args=[request.pk]))
    assert "add-new-dataset" in resp.text
    resp = resp.click(linkid="add-new-dataset")
    assert resp.request.path_qs == \
           reverse('resource-subclass-add', args=[organization2.pk]) + f"?next={reverse('request-datasets', args=[request.pk])}"


@pytest.mark.django_db
def test_add_existing_dataset_to_request_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    request = RequestFactory()
    organization = OrganizationFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    resp = app.get(reverse('request-datasets', args=[request.pk]))
    assert "add-dataset" not in resp.text
    resp = app.get(reverse('request-datasets-edit', args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_add_existing_dataset_to_request_with_representative_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(organization=organization)
    app.set_user(user)
    request = RequestFactory()
    organization = OrganizationFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    resp = app.get(reverse('request-datasets', args=[request.pk]))
    assert "add-dataset" in resp.text
    resp = app.get(reverse('request-datasets-edit', args=[request.pk]))
    assert resp.request.path_qs == reverse('request-datasets-edit', args=[request.pk])


@pytest.mark.django_db
def test_add_existing_dataset_to_request_with_organization_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    organization2 = OrganizationFactory()
    user = UserFactory(organization=organization2)
    app.set_user(user)
    request = RequestFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    RepresentativeFactory(
        organization=organization2,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization2),
        object_id=organization2.pk
    )
    resp = app.get(reverse('request-datasets', args=[request.pk]))
    assert "add-dataset" in resp.text
    resp = app.get(reverse('request-datasets-edit', args=[request.pk]))
    assert resp.request.path_qs == reverse('request-datasets-edit', args=[request.pk])


@pytest.mark.django_db
def test_open_data_coordinator_cannot_see_non_public_datasets(app: "DjangoTestApp"):
    org = OrganizationFactory()
    user = UserFactory(organization=org)
    app.set_user(user)

    RepresentativeFactory(
        user=user,
        organization=org,
        content_type=ContentType.objects.get_for_model(org),
        role=Representative.OPEN_DATA_COORDINATOR,
        object_id=org.pk
    )

    request = RequestFactory()

    RequestAssignmentFactory(organization=org, request=request, status=request.status)

    public_ds = DatasetFactory(organization=org, access_rights=Dataset.PUBLIC)
    restricted_ds = DatasetFactory(organization=org, access_rights=Dataset.RESTRICTED)
    non_public_ds = DatasetFactory(organization=org, access_rights=Dataset.NON_PUBLIC)

    for ds in [public_ds, restricted_ds, non_public_ds]:
        RequestObjectFactory(
            request=request, content_type=ContentType.objects.get_for_model(Dataset), object_id=ds.pk
        )

    url = reverse("request-datasets-edit", args=[request.pk])
    resp = app.get(url)

    assert str(public_ds.id) in resp.text
    assert str(restricted_ds.id) in resp.text
    assert str(non_public_ds.id) not in resp.text


@pytest.mark.django_db
def test_remove_dataset_from_request_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    request = RequestFactory()
    organization = OrganizationFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    dataset = DatasetFactory()
    RequestObjectFactory(
        request=request,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk
    )
    resp = app.get(reverse('request-datasets', args=[request.pk]))
    assert f"remove-dataset-{dataset.pk}-btn" not in resp.text
    resp = app.get(reverse('request-dataset-remove', args=[request.pk, dataset.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_remove_dataset_from_request_with_representative_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(organization=organization)
    app.set_user(user)
    request = RequestFactory()
    organization = OrganizationFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    dataset = DatasetFactory()
    RequestObjectFactory(
        request=request,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk
    )

    app.post(reverse('request-dataset-remove', args=[request.pk, dataset.pk]))

    request.refresh_from_db()
    assert request.pk
    assert not RequestObject.objects.filter(
        object_id=dataset.pk,
        content_type=ContentType.objects.get_for_model(dataset),
    ).exists()


@pytest.mark.django_db
def test_remove_dataset_from_request_with_organization_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    organization2 = OrganizationFactory()
    user = UserFactory(organization=organization2)
    app.set_user(user)
    request = RequestFactory()
    RequestAssignmentFactory(
        organization=organization,
        request=request,
        status=request.status
    )
    RepresentativeFactory(
        organization=organization2,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization2),
        object_id=organization2.pk
    )
    dataset = DatasetFactory()
    RequestObjectFactory(
        request=request,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk
    )

    app.post(reverse('request-dataset-remove', args=[request.pk, dataset.pk]))

    request.refresh_from_db()
    assert request.pk
    assert not RequestObject.objects.filter(
        object_id=dataset.pk,
        content_type=ContentType.objects.get_for_model(dataset),
    ).exists()


@pytest.mark.django_db
@patch('vitrina.requests.views.email')
def test_request_create_email_only_to_users_with_flag(mock_email, app: DjangoTestApp):
    creator = UserFactory(is_staff=True)
    UserFactory(email='with_flag@test.com', receive_request_email=True)
    UserFactory(email='without_flag@test.com', receive_request_email=False)

    app.set_user(creator)
    form = app.get(reverse("request-create")).forms['request-form']
    form['title'] = "Test Request"
    form['description'] = "Test Description"
    form.submit()

    mock_email.assert_called_once()
    email_list = list(mock_email.call_args[0][0])

    assert 'with_flag@test.com' in email_list
    assert 'without_flag@test.com' not in email_list


@pytest.mark.django_db
@patch('vitrina.requests.views.email')
def test_request_create_no_email_when_no_users_have_flag(mock_email, app: DjangoTestApp):
    creator = UserFactory(is_staff=True)
    UserFactory(email='user1@test.com', receive_request_email=False)
    UserFactory(email='user2@test.com', receive_request_email=False)

    app.set_user(creator)
    form = app.get(reverse("request-create")).forms['request-form']
    form['title'] = "Test Request"
    form['description'] = "Test Description"
    form.submit()

    if mock_email.called:
        email_list = list(mock_email.call_args[0][0])
        assert len(email_list) == 0