import io
from unittest.mock import patch

import pytest
from datetime import datetime

from PIL import Image
from django_recaptcha.client import RecaptchaResponse
from freezegun import freeze_time
import pytz
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse

from django_webtest import DjangoTestApp
from itsdangerous import URLSafeSerializer
from webtest import Upload

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative, Organization
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan
from vitrina.requests.factories import RequestFactory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.mark.django_db
def test_organization_detail_tab(app: DjangoTestApp):
    parent_organization = OrganizationFactory()
    organization = parent_organization.add_child(instance=OrganizationFactory.build())
    resp = app.get(organization.get_absolute_url())
    assert list(resp.context['ancestors']) == [parent_organization]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Informacija"]


@pytest.mark.django_db
def test_organization_members_tab(app: DjangoTestApp):
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    content_type = ContentType.objects.get_for_model(Organization)
    representative1 = RepresentativeFactory(
        content_type=content_type,
        object_id=organization1.pk,
    )
    RepresentativeFactory(
        content_type=content_type,
        object_id=organization2.pk,
    )
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    app.set_user(admin)
    resp = app.get(reverse('organization-members', args=[organization1.pk]))
    assert list(resp.context['members']) == [representative1]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == [
        "Organizacijos atstovai",
    ]


@pytest.mark.haystack
def test_organization_dataset_tab(app: DjangoTestApp):
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    dataset1 = DatasetFactory(organization=organization1)
    dataset2 = DatasetFactory(organization=organization2)
    resp = app.get(reverse('organization-datasets', args=[organization1.pk]))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [dataset1.pk]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Duomenų rinkiniai"]


@pytest.fixture
def organizations():
    with freeze_time(timezone.localize(datetime(2022, 8, 22, 10, 30))):
        organization1 = OrganizationFactory(
            slug="org1",
            title="Organization 1",
            jurisdiction="Jurisdiction1"
        )
    with freeze_time(timezone.localize(datetime(2022, 10, 22, 10, 30))):
        organization2 = OrganizationFactory(
            slug="org2",
            title="Organization 2",
            jurisdiction="Jurisdiction2"
        )
    with freeze_time(datetime(2022, 9, 22, 10, 30)):
        organization3 = OrganizationFactory(
            slug="org3",
            title="Organization 3",
            jurisdiction="Jurisdiction2"
        )
    return [organization1, organization2, organization3]


@pytest.mark.django_db
def test_search_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[0], organizations[1], organizations[2]]


@pytest.mark.django_db
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "doesnt-match"))
    assert len(resp.context['object_list']) == 0


@pytest.mark.django_db
def test_search_with_query_that_matches_one(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "1"))
    assert list(resp.context['object_list']) == [organizations[0]]


@pytest.mark.django_db
def test_search_with_query_that_matches_all(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "organization"))
    assert list(resp.context['object_list']) == [organizations[0], organizations[1], organizations[2]]


@pytest.mark.django_db
def test_filter_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[0], organizations[1], organizations[2]]
    assert resp.context['selected_jurisdiction'] is None
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction2',
            'query': "?jurisdiction=Jurisdiction2",
            'count': 2
        },
        {
            'title': 'Jurisdiction1',
            'query': "?jurisdiction=Jurisdiction1",
            'count': 1
        },
    ]


@pytest.mark.django_db
def test_filter_with_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=Jurisdiction1" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[0]]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction1"
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction1',
            'query': "?jurisdiction=Jurisdiction1",
            'count': 1
        }
    ]


@pytest.mark.django_db
def test_filter_with_other_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=Jurisdiction2" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2]]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction2"
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction2',
            'query': "?jurisdiction=Jurisdiction2",
            'count': 2
        }
    ]


@pytest.mark.django_db
def test_filter_with_non_existent_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=doesnotexist" % reverse('organization-list'))
    assert len(resp.context['object_list']) == 0
    assert resp.context['selected_jurisdiction'] == "doesnotexist"
    assert resp.context['jurisdictions'] == []


@pytest.mark.django_db
def test_filter_with_jurisdiction_and_title(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=1&jurisdiction=Jurisdiction1" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[0]]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction1"
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction1',
            'query': "?q=1&jurisdiction=Jurisdiction1",
            'count': 1
        },
    ]


@pytest.mark.django_db
def test_filter_with_query_containing_special_characters(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization \"<'>\\", jurisdiction="Jurisdiction\"<'>\\")
    resp = app.get("%s?q=\"<'>\\&jurisdiction=Jurisdiction\"<'>\\" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organization]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction\"<'>\\"
    assert resp.context['jurisdictions'] == [
        {
            'title': "Jurisdiction\"<'>\\",
            'query': "?q=\"<'>\\&jurisdiction=Jurisdiction\"<'>\\",
            'count': 1
        },
    ]


@pytest.fixture
def representative_data():
    manager = User.objects.create_user(
        email="manager@gmail.com",
        password="manager123",
        first_name="Manager",
        last_name="User",
        phone="861234567"
    )
    coordinator = User.objects.create_user(
        email="coordinator@gmail.com",
        password="coordinator123",
        first_name="Coordinator",
        last_name="User",
        phone="869876543"
    )
    organization = OrganizationFactory()
    content_type = ContentType.objects.get_for_model(Organization)
    representative_manager = RepresentativeFactory(
        role="manager",
        content_type=content_type,
        object_id=organization.pk
    )
    representative_coordinator = RepresentativeFactory(
        role="coordinator",
        content_type=content_type,
        object_id=organization.pk,
        user=coordinator
    )
    return {
        'manager': manager,
        'coordinator': coordinator,
        'organization': organization,
        'representative_manager': representative_manager,
        'representative_coordinator': representative_coordinator
    }


@pytest.mark.django_db
def test_representative_create_without_permission(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['manager'])
    resp = app.get(reverse('representative-create', kwargs={
        'organization_id': representative_data['organization'].pk
    }), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_representative_create_with_existing_user(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-create', kwargs={
        'organization_id': representative_data['organization'].pk
    })).forms['representative-form']
    form['email'] = "manager@gmail.com"
    form['role'] = "coordinator"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert Representative.objects.filter(email="manager@gmail.com").count() == 1
    assert Representative.objects.filter(email="manager@gmail.com").first().content_object == \
           representative_data['organization']
    assert Representative.objects.filter(email="manager@gmail.com").first().user == representative_data['manager']
    assert Representative.objects.filter(
        email="manager@gmail.com"
    ).first().user.organization == representative_data['organization']


@pytest.mark.django_db
def test_representative_create_without_user(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-create', kwargs={
        'organization_id': representative_data['organization'].pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert Representative.objects.filter(email="new@gmail.com").count() == 1
    assert Representative.objects.filter(email="new@gmail.com").first().content_object == \
           representative_data['organization']
    assert Representative.objects.filter(email="new@gmail.com").first().user is None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@gmail.com"]


@pytest.mark.django_db
def test_representative_create_without_user_for_two_organizations(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    app.set_user(user)

    form = app.get(reverse('representative-create', kwargs={
        'organization_id': organization1.pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    form.submit()

    form = app.get(reverse('representative-create', kwargs={
        'organization_id': organization2.pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    resp = form.submit()

    assert len(resp.context['form'].errors) == 1
    assert Representative.objects.filter(email="new@gmail.com").count() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@gmail.com"]


@pytest.mark.django_db
def test_representative_create_without_user_for_two_objects(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    organization = OrganizationFactory()
    dataset = DatasetFactory()
    app.set_user(user)

    form = app.get(reverse('representative-create', kwargs={
        'organization_id': organization.pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    form.submit()

    form = app.get(reverse('dataset-representative-create', kwargs={
        'pk': dataset.pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    form.submit()

    assert Representative.objects.filter(email="new@gmail.com").count() == 2
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@gmail.com"]


@pytest.mark.django_db
def test_representative_subscription(app: DjangoTestApp, representative_data):
    subscriptions_before = Subscription.objects.all()
    assert len(subscriptions_before) == 0

    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse('representative-create', kwargs={
        'organization_id': representative_data['organization'].pk
    })).forms['representative-form']
    form['email'] = "manager@gmail.com"
    form['role'] = "manager"
    form['subscribe'] = True
    resp = form.submit()

    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert Representative.objects.filter(email="manager@gmail.com").count() == 1
    assert Representative.objects.filter(email="manager@gmail.com").first().content_object == \
           representative_data['organization']
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["manager@gmail.com"]

    subscription = Subscription.objects.get(user=representative_data['manager'])
    assert subscription.sub_type == Subscription.ORGANIZATION


@pytest.mark.django_db
def test_register_after_adding_representative(csrf_exempt_django_app: DjangoTestApp, representative_data):
    new_representative = RepresentativeFactory(
        email="new@gmail.com",
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=representative_data['organization'].pk,
        user=None
    )
    serializer = URLSafeSerializer(settings.SECRET_KEY)
    token = serializer.dumps({"representative_id": new_representative.pk})

    with patch('django_recaptcha.fields.client.submit') as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = csrf_exempt_django_app.post(reverse('representative-register', kwargs={'token': token}), {
            'first_name': "New",
            'last_name': "User",
            'email': "new@gmail.com",
            'password1': "test123?",
            'password2': "test123?",
            'agree_to_terms': True,
            "g-recaptcha-response": "PASSED",
        })
        new_representative.refresh_from_db()
        assert resp.status_code == 302
        assert resp.url == reverse('home')
        assert User.objects.filter(email='new@gmail.com').count() == 1
        assert new_representative.user == User.objects.filter(email='new@gmail.com').first()
        assert new_representative.user.organization == representative_data['organization']


@pytest.mark.django_db
def test_representative_update_without_permission(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['manager'])
    resp = app.get(reverse('representative-create', kwargs={
        'organization_id': representative_data['organization'].pk
    }), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_representative_update_no_coordinators(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-update', kwargs={
        'organization_id': representative_data['organization'].pk,
        'pk': representative_data['representative_coordinator'].pk
    })).forms['representative-form']
    form['role'] = "manager"
    resp = form.submit()
    assert len(resp.context['form'].errors) == 1


@pytest.mark.django_db
def test_representative_update_with_correct_data(app: DjangoTestApp, representative_data):
    representative_data['representative_manager'].user = representative_data['manager']
    representative_data['representative_manager'].save()
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-update', kwargs={
        'organization_id': representative_data['organization'].pk,
        'pk': representative_data['representative_manager'].pk
    })).forms['representative-form']
    form['role'] = "coordinator"
    resp = form.submit()
    representative_data['representative_manager'].refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert representative_data['representative_manager'].role == "coordinator"
    assert representative_data['representative_manager'].user.organization == representative_data['organization']


@pytest.mark.django_db
def test_organization_plan_create_with_no_provider(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    app.set_user(rep.user)

    form = app.get(reverse('organization-plans-create', args=[organization.pk])).forms['plan-form']
    form['title'] = "Test plan"
    form['description'] = "Plan for testing"
    form['provider'] = ''
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        "Turi būti nurodytas paslaugų teikėjas arba paslaugų teikėjo pavadinimas."
    ]]


@pytest.mark.django_db
def test_organization_plan_create_with_multiple_providers(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    app.set_user(rep.user)

    form = app.get(reverse('organization-plans-create', args=[organization.pk])).forms['plan-form']
    form['title'] = "Test plan"
    form['description'] = "Plan for testing"
    form['provider'].force_value(organization.pk)
    form['provider_title'] = "Provider"
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        "Turi būti nurodytas arba paslaugų teikėjas, arba paslaugų teikėjo pavadinimas, bet ne abu."
    ]]


@pytest.mark.django_db
def test_organization_plan_create(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    rep.user.organization = organization
    rep.user.save()
    app.set_user(rep.user)

    form = app.get(reverse('organization-plans-create', args=[organization.pk])).forms['plan-form']
    form['title'] = "Test plan"
    form['description'] = "Plan for testing"
    resp = form.submit()

    assert resp.url == reverse('organization-plans', args=[organization.pk])
    assert Plan.objects.count() == 1
    assert Plan.objects.first().title == 'Test plan'
    assert Plan.objects.first().description == 'Plan for testing'
    assert Plan.objects.first().receiver == organization


@pytest.mark.django_db
def test_organization_plan_update(app: DjangoTestApp):
    plan = PlanFactory()
    ct = ContentType.objects.get_for_model(plan.receiver)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=plan.receiver.pk,
        role=Representative.MANAGER
    )
    app.set_user(rep.user)

    form = app.get(reverse('plan-change', args=[plan.receiver.pk, plan.pk])).forms['plan-form']
    form['title'] = "Test plan (updated)"
    form['provider'].force_value(plan.receiver.pk)
    resp = form.submit()

    assert resp.url == reverse('plan-detail', args=[plan.receiver.pk, plan.pk])
    assert Plan.objects.count() == 1
    assert Plan.objects.first().title == "Test plan (updated)"
    assert Plan.objects.first().provider == plan.receiver


@pytest.mark.django_db
def test_organization_merge_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    organization = OrganizationFactory()
    resp = app.get(reverse('merge-organizations', args=[organization.pk]), expect_errors=True)

    assert resp.status_code == 403


@pytest.mark.django_db
def test_organization_merge(app: DjangoTestApp):
    user = UserFactory(is_superuser=True)
    app.set_user(user)

    organization = OrganizationFactory()
    organization_id = organization.pk
    merge_organization = OrganizationFactory()

    dataset = DatasetFactory(organization=organization)
    request = RequestFactory()
    request.organizations.add(organization)
    representative = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )

    form = app.get(reverse('confirm-organization-merge', args=[
        organization.pk,
        merge_organization.pk
    ])).forms['confirm-merge-form']
    resp = form.submit()

    assert resp.url == reverse('organization-detail', args=[merge_organization.pk])
    assert Organization.objects.filter(pk=organization_id).count() == 0
    assert list(merge_organization.dataset_set.all()) == [dataset]
    assert list(merge_organization.request_set.all()) == [request]
    assert list(Representative.objects.filter(
        content_type=ContentType.objects.get_for_model(merge_organization),
        object_id=merge_organization.pk
    )) == [representative]


@pytest.mark.django_db
def test_organization_open_plans(app: DjangoTestApp):
    organization = OrganizationFactory()
    PlanFactory(is_closed=True, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)

    resp = app.get(reverse('organization-plans', args=[organization.pk]))
    assert len(resp.context['plans']) == 2


@pytest.mark.django_db
def test_organization_closed_plans(app: DjangoTestApp):
    organization = OrganizationFactory()
    PlanFactory(is_closed=True, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)

    resp = app.get("%s?status=closed" % reverse('organization-plans', args=[organization.pk]))
    assert len(resp.context['plans']) == 1


@pytest.mark.django_db
def test_change_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    response = app.get(reverse('organization-change', kwargs={'pk': org.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp):
    org = OrganizationFactory()
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse('organization-change', kwargs={'pk': org.id}))
    assert response.status_code == 302
    assert str(org.id) in response.location


def generate_photo_file(height, length) -> bytes:
    file = io.BytesIO()
    image = Image.new('RGBA', size=(height, length), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'img.png'
    return file.getvalue()


@pytest.mark.django_db
def test_change_form_correct_login(app: DjangoTestApp):
    org = OrganizationFactory()
    jurisdiction = OrganizationFactory(role='test')

    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse('organization-change', kwargs={'pk': org.id})).forms['organization-form']

    form['title'] = 'Edited title'
    form['description'] = 'edited org description'
    form['jurisdiction'] = jurisdiction.id
    form['image'] = Upload('img.png', generate_photo_file(300, 300), 'image')

    resp = form.submit()
    org.refresh_from_db()

    assert resp.status_code == 302
    assert resp.url == reverse('organization-detail', kwargs={'pk': org.id})
    assert org.title == 'Edited title'
    assert org.description == 'edited org description'


@pytest.mark.django_db
def test_click_edit_button(app: DjangoTestApp):
    org = OrganizationFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(reverse('organization-detail', kwargs={'pk': org.id}))
    response.click(linkid='change_organization')
    assert response.status_code == 200
