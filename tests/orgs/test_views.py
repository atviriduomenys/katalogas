import io
from unittest.mock import patch, Mock
from bs4 import BeautifulSoup

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
from vitrina.api.factories import APIKeyFactory
from vitrina.api.models import ApiKey
from vitrina.classifiers.factories import AreaOfManagementFactory
from vitrina.classifiers.models import AreaOfManagement
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Contact
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory, ViispRepresentativeFactory
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
        "Tvarkytojai",
    ]


@pytest.mark.haystack
def test_organization_dataset_tab(app: DjangoTestApp):
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    dataset1 = DatasetFactory(organization=organization1)
    dataset2 = DatasetFactory(organization=organization2)
    resp = app.get(reverse('organization-datasets', args=[organization1.pk]))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [dataset1.pk]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Duomenų ištekliai"]


@pytest.fixture
def organizations():
    with freeze_time(timezone.localize(datetime(2022, 8, 22, 10, 30))):
        organization1 = OrganizationFactory(
            slug="org1",
            title="Organization 1",
            jurisdiction=AreaOfManagement.objects.get(id=1),
        )
    with freeze_time(timezone.localize(datetime(2022, 10, 22, 10, 30))):
        jurisdiction2 = AreaOfManagementFactory(id=30)
        organization2 = OrganizationFactory(
            slug="org2",
            title="Organization 2",
            jurisdiction=jurisdiction2
        )
    with freeze_time(datetime(2022, 9, 22, 10, 30)):
        organization3 = OrganizationFactory(
            slug="org3",
            title="Organization 3",
            jurisdiction=jurisdiction2,
        )
    return [organization1, organization2, organization3]


@pytest.mark.haystack
def test_search_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organizations[0].pk, organizations[1].pk, organizations[2].pk]


@pytest.mark.django_db
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "doesnt-match"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == []


@pytest.mark.haystack
def test_search_with_query_that_matches_one(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "1"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organizations[0].pk]


@pytest.mark.haystack
def test_search_with_query_that_matches_all(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "organization"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organizations[0].pk, organizations[1].pk,
                                                                    organizations[2].pk]


@pytest.mark.haystack
def test_filter_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organizations[0].pk, organizations[1].pk,
                                                                    organizations[2].pk]
    assert resp.context['selected_jurisdiction'] is None
    assert resp.context['jurisdictions'] == [
        {
            'id': 30,
            'title': 'Jurisdiction30',
            'query': "?jurisdiction=30",
            'count': 2
        },
        {
            'id': 1,
            'title': 'Nepriskirta',
            'query': "?jurisdiction=1",
            'count': 1
        },
    ]


@pytest.mark.haystack
def test_filter_with_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=1" % reverse('organization-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organizations[0].pk]
    assert resp.context['selected_jurisdiction'] == "Nepriskirta"
    assert resp.context['jurisdictions'] == [
        {
            'id': 1,
            'title': 'Nepriskirta',
            'query': "?jurisdiction=1",
            'count': 1
        }
    ]


@pytest.mark.haystack
def test_filter_with_other_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=30" % reverse('organization-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organizations[1].pk,
                                                                    organizations[2].pk]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction30"
    assert resp.context['jurisdictions'] == [
        {
            'id': 30,
            'title': 'Jurisdiction30',
            'query': "?jurisdiction=30",
            'count': 2
        }
    ]


@pytest.mark.haystack
def test_filter_with_non_existent_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=0" % reverse('organization-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == []
    assert resp.context['selected_jurisdiction'] is None
    assert resp.context['jurisdictions'] == []


@pytest.mark.haystack
def test_filter_with_jurisdiction_and_title(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=2&jurisdiction=30" % reverse('organization-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organizations[1].pk]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction30"
    assert resp.context['jurisdictions'] == [
        {
            'id': 30,
            'title': 'Jurisdiction30',
            'query': "?q=2&jurisdiction=30",
            'count': 1
        },
    ]


@pytest.mark.haystack
def test_filter_with_query_containing_special_characters(app: DjangoTestApp):
    jurisdiction = AreaOfManagementFactory(id=30, name_lt="Jurisdiction\"<'>\\", name_en="Jurisdiction\"<'>\\")
    organization = OrganizationFactory(title="Organization \"<'>\\", jurisdiction=jurisdiction)
    resp = app.get("%s?q=\"<'>\\&jurisdiction=30" % reverse('organization-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [organization.pk]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction\"<'>\\"
    assert resp.context['jurisdictions'] == [
        {
            'id' : 30,
            'title': "Jurisdiction\"<'>\\",
            'query': "?q=\"<'>\\&jurisdiction=30",
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
    viisp_coordinator = User.objects.create_user(
        email="viispcoordinator@gmail.com",
        password="coordinator123",
        first_name="Viisp Coordinator",
        last_name="User",
        phone="869876543",
        is_viisp_login=True,
        viisp_company_code=organization.company_code
    )
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
    representative_viisp_coordinator = RepresentativeFactory(
        role="coordinator",
        content_type=content_type,
        object_id=organization.pk,
        user=viisp_coordinator
    )
    return {
        'manager': manager,
        'coordinator': coordinator,
        'viisp_coordinator': viisp_coordinator,
        'organization': organization,
        'representative_manager': representative_manager,
        'representative_coordinator': representative_coordinator,
        'representative_viisp_coordinator': representative_viisp_coordinator
    }


@pytest.mark.django_db
def test_representative_create_without_permission(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['manager'])
    resp = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
    }), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_representative_create_with_existing_user(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
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
def test_representative_create_can_make_agreements_disabled(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
    })).forms['representative-form']
    assert 'disabled' in form["can_make_agreements"].attrs
    form['email'] = "manager@gmail.com"
    form['role'] = "coordinator"
    form['can_make_agreements'] = True
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    representative_qs = Representative.objects.filter(email="manager@gmail.com")
    assert representative_qs.count() == 1
    representative = representative_qs.first()
    assert representative.content_object == representative_data['organization']
    assert representative.user == representative_data['manager']
    assert representative.user.organization == representative_data['organization']
    assert not representative.can_make_agreements

@pytest.mark.django_db
def test_representative_create_with_can_make_agreements_rights(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['viisp_coordinator'])
    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
    })).forms['representative-form']
    form['email'] = "manager@gmail.com"
    form['role'] = "coordinator"
    form['can_make_agreements'] = True
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    representative_qs = Representative.objects.filter(email="manager@gmail.com")
    assert representative_qs.count() == 1
    representative = representative_qs.first()
    assert representative.content_object == representative_data['organization']
    assert representative.user == representative_data['manager']
    assert representative.user.organization == representative_data['organization']
    assert representative.can_make_agreements

@pytest.mark.django_db
def test_representative_create_without_user(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
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
        'pk': organization1.pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    form.submit()

    form = app.get(reverse('representative-create', kwargs={
        'pk': organization2.pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    form.submit()

    assert Representative.objects.filter(email="new@gmail.com").count() == 2
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@gmail.com"]


@pytest.mark.django_db
def test_representative_create_invalid_phone(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
    })).forms['representative-form']
    form['email'] = "new@gmail.com"
    form['role'] = "manager"
    form['phone'] = "123456"
    resp = form.submit()
    assert resp.status_code == 200
    assert "Primtini formatai: +3706XXXXXXX, 0XXXXXXXX)" in resp.context['form'].errors['phone'][0]
    assert Representative.objects.filter(email="new@gmail.com").count() == 0


@pytest.mark.django_db
def test_representative_create_valid_phone(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])

    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
    })).forms['representative-form']
    form['email'] = "new1@gmail.com"
    form['role'] = "manager"
    form['phone'] = "+37061234567"
    resp = form.submit()
    assert resp.status_code == 302
    rep_queryset = Representative.objects.filter(email="new1@gmail.com")
    assert rep_queryset.count() == 1
    assert rep_queryset.first().phone == "+37061234567"

    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
    })).forms['representative-form']
    form['email'] = "new2@gmail.com"
    form['role'] = "manager"
    form['phone'] = "061234567"
    resp = form.submit()
    assert resp.status_code == 302
    rep_queryset = Representative.objects.filter(email="new2@gmail.com")
    assert rep_queryset.count() == 1
    assert rep_queryset.first().phone == "061234567"


@pytest.mark.django_db
@pytest.mark.parametrize("can_write", [True, False])
def test_representative_create_with_can_write_flag(app: DjangoTestApp, representative_data: dict, can_write: bool):
    app.set_user(representative_data["coordinator"])
    form = app.get(
        reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})
    ).forms["representative-form"]
    form["role"] = "manager"
    form["email"] = "new@gmail.com"
    form["can_write"] = can_write

    response = form.submit()
    assert response.status_code == 302
    representative = Representative.objects.filter(email="new@gmail.com").first()
    assert representative.can_write == can_write


@pytest.mark.django_db
def test_representative_update_phone(app: DjangoTestApp, representative_data):
    representative_data['representative_manager'].user = representative_data['manager']
    representative_data['representative_manager'].save()
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('representative-update', kwargs={
        'pk': representative_data['organization'].pk,
        'representative_id': representative_data['representative_manager'].pk
    })).forms['representative-form']
    form['phone'] = "061234567"
    resp = form.submit()
    assert resp.status_code == 302
    representative_data['representative_manager'].refresh_from_db()
    assert representative_data['representative_manager'].phone == "061234567"


@pytest.mark.django_db
def test_representative_subscription(app: DjangoTestApp, representative_data):
    subscriptions_before = Subscription.objects.all()
    assert len(subscriptions_before) == 0

    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse('representative-create', kwargs={
        'pk': representative_data['organization'].pk
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
def test_register_after_adding_representative(app: DjangoTestApp, representative_data):
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
        resp = app.post(reverse('representative-register', kwargs={'token': token}), {
            'first_name': "New",
            'last_name': "User",
            'email': "new@gmail.com",
            'password1': "v)Yxu*DF8}rj~(Sz!-X:Ws",
            'password2': "v)Yxu*DF8}rj~(Sz!-X:Ws",
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
        'pk': representative_data['organization'].pk
    }), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_representative_update_no_coordinators(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['coordinator'])
    representative_data['representative_viisp_coordinator'].role = 'manager'
    representative_data['representative_viisp_coordinator'].save()
    form = app.get(reverse('representative-update', kwargs={
        'pk': representative_data['organization'].pk,
        'representative_id': representative_data['representative_coordinator'].pk
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
        'pk': representative_data['organization'].pk,
        'representative_id': representative_data['representative_manager'].pk
    })).forms['representative-form']
    form['role'] = "coordinator"
    resp = form.submit()
    representative_data['representative_manager'].refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert representative_data['representative_manager'].role == "coordinator"
    assert representative_data['representative_manager'].user.organization == representative_data['organization']


@pytest.mark.django_db
def test_representative_update_can_make_agreements(app: DjangoTestApp, representative_data):
    app.set_user(representative_data['viisp_coordinator'])
    form = app.get(reverse('representative-update', kwargs={
        'pk': representative_data['organization'].pk,
        'representative_id': representative_data['representative_manager'].pk
    })).forms['representative-form']
    form['can_make_agreements'] = True
    resp = form.submit()
    representative_data['representative_manager'].refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert representative_data['representative_manager'].can_make_agreements


@pytest.mark.django_db
@pytest.mark.parametrize("can_write", [True, False])
def test_representative_update_can_write_flag(app: DjangoTestApp, representative_data: dict, can_write: bool):
    representative = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(representative_data["organization"]),
        object_id=representative_data["organization"].pk,
        role=Representative.MANAGER,
        can_write=can_write,
    )

    app.set_user(representative_data["coordinator"])
    form = app.get(
        reverse("representative-update", kwargs={
            "pk": representative_data["organization"].pk, "representative_id": representative.pk
        })
    ).forms["representative-form"]
    form["can_write"] = not can_write

    response = form.submit()
    assert response.status_code == 302
    representative.refresh_from_db()
    assert representative.can_write == (not can_write)


@pytest.mark.django_db
def test_organization_plan_create_with_no_publisher(app: DjangoTestApp):
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
    form['publisher'] = ''
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        "Turi būti nurodytas paslaugų teikėjas arba paslaugų teikėjo pavadinimas."
    ]]


@pytest.mark.django_db
def test_organization_plan_create_with_multiple_publishers(app: DjangoTestApp):
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
    form['publisher'].force_value(organization.pk)
    form['provider_title'] = "Publisher"
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
    form['publisher'].force_value(plan.receiver.pk)
    resp = form.submit()

    assert resp.url == reverse('plan-detail', args=[plan.receiver.pk, plan.pk])
    assert Plan.objects.count() == 1
    assert Plan.objects.first().title == "Test plan (updated)"
    assert Plan.objects.first().publisher == plan.receiver


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
    representative = ViispRepresentativeFactory()
    org = representative.content_object
    jurisdiction = AreaOfManagementFactory(id=30, name_lt="Jurisdiction30", name_en="Jurisdiction30")

    user = representative.user
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
    representative = ViispRepresentativeFactory()
    org = representative.content_object
    user = representative.user
    app.set_user(user)
    response = app.get(reverse('organization-detail', kwargs={'pk': org.id}))
    response.click(linkid='change_organization')
    assert response.status_code == 200


@pytest.mark.django_db
def test_contact_tab_access_coordinator(app, representative_data):
    app.set_user(representative_data['coordinator'])

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': representative_data['organization'].pk
    }))

    assert resp.status_code == 200
    assert 'Kontaktai' in resp.text
    assert 'contacts/add' in resp.text


@pytest.mark.django_db
def test_contact_tab_access_denied_for_manager(app, representative_data):
    app.set_user(representative_data['manager'])

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': representative_data['organization'].pk
    }), expect_errors=True)

    assert resp.status_code == 403


@pytest.mark.django_db
def test_contact_tab_display_org_contacts(app, representative_data):
    app.set_user(representative_data['coordinator'])
    organization = representative_data['organization']

    Contact.objects.create(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        email="org@test.com",
        phone="+37061234567"
    )

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': organization.pk
    }))

    assert resp.status_code == 200
    assert 'org@test.com' in resp.text
    assert '+37061234567' in resp.text
    assert organization.title in resp.text


@pytest.mark.django_db
def test_contact_tab_display_user_contacts(app, representative_data):
    app.set_user(representative_data['coordinator'])
    organization = representative_data['organization']
    user = representative_data['manager']

    Contact.objects.create(
        organization=organization,
        content_type=ContentType.objects.get_for_model(user),
        object_id=user.pk,
        email="user@test.com",
        phone="+37061234567"
    )

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': organization.pk
    }))

    assert resp.status_code == 200
    assert 'user@test.com' in resp.text
    assert '+37061234567' in resp.text
    assert user.get_full_name() in resp.text


@pytest.mark.django_db
def test_contact_tab_display_multiple_contacts(app, representative_data):
    app.set_user(representative_data['coordinator'])
    organization = representative_data['organization']
    user1 =  UserFactory(organization=organization)
    user2 = UserFactory(organization=organization)

    contacts = [
        Contact.objects.create(
            organization=organization,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            email="org@test.com",
            phone="+37061234567"
        ),
        Contact.objects.create(
            organization=organization,
            content_type=ContentType.objects.get_for_model(user1),
            object_id=user1.pk,
            email="user1@test.com",
            phone="+37067654321"
        ),
        Contact.objects.create(
            organization=organization,
            content_type=ContentType.objects.get_for_model(user2),
            object_id=user2.pk,
            email="user2@test.com",
            phone="+37061111111"
        )
    ]

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': organization.pk
    }))

    assert resp.status_code == 200

    for contact in contacts:
        assert contact.email in resp.text
        assert contact.phone in resp.text

    assert organization.title in resp.text
    assert user1.get_full_name() in resp.text
    assert user2.get_full_name() in resp.text


@pytest.mark.django_db
def test_contact_tab_pagination(app, representative_data):
    app.set_user(representative_data['coordinator'])
    organization = representative_data['organization']

    for i in range(15):
        user = UserFactory(organization=organization)
        Contact.objects.create(
            organization=organization,
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
            email=f"user{i}@test.com"
        )

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': organization.pk
    }))

    assert resp.status_code == 200
    assert 'page=2' in resp.text

    soup = BeautifulSoup(resp.content, 'html.parser')
    rows = soup.find('table').find('tbody').find_all('tr')
    assert len(rows) == 10


@pytest.mark.django_db
def test_contact_tab_empty_state(app, representative_data):
    app.set_user(representative_data['coordinator'])

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': representative_data['organization'].pk
    }))

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, 'html.parser')
    rows = soup.find('table')
    assert rows is None


@pytest.mark.django_db
def test_contact_tab_actions_coordinator(app, representative_data):
    app.set_user(representative_data['coordinator'])
    organization = representative_data['organization']

    contact = Contact.objects.create(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        email="test@test.com"
    )

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': organization.pk
    }))

    assert resp.status_code == 200
    assert f'contacts/{contact.pk}/change' in resp.text
    assert f'contacts/{contact.pk}/delete' in resp.text


@pytest.mark.django_db
def test_contact_create_for_org(app, representative_data):
    org = representative_data['organization']
    app.set_user(representative_data['coordinator'])
    form = app.get(reverse('contact-create', kwargs={
        'pk': org.pk
    })).forms['contact-form']

    form['contact'] = f"org-{org.pk}"
    form['email'] = "org@test.com"
    form['phone'] = "+37061234567"

    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-contacts', kwargs={'pk': org.pk})

    contact = Contact.objects.first()
    assert contact.content_type == ContentType.objects.get_for_model(org)
    assert contact.object_id == org.pk
    assert contact.email == "org@test.com"
    assert contact.phone == "+37061234567"
    assert contact.organization == org

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': org.pk
    }))
    assert resp.status_code == 200
    assert contact.email in resp.text
    assert contact.phone in resp.text
    assert org.title in resp.text


@pytest.mark.django_db
def test_contact_create_for_user_valid_data(app, representative_data):
    org = representative_data['organization']
    app.set_user(representative_data['coordinator'])
    coordinator = representative_data['coordinator']
    form = app.get(reverse('contact-create', kwargs={
        'pk': org.pk
    })).forms['contact-form']
    form['contact'] = f"user-{coordinator.pk}"
    form['email'] = "user@test.com"
    form['phone'] = "+37061234567"
    form['position'] = "Tester"

    resp = form.submit()
    assert resp.status_code == 302

    contact = Contact.objects.first()
    assert contact.content_type == ContentType.objects.get_for_model(coordinator)
    assert contact.object_id == coordinator.pk
    assert contact.email == "user@test.com"
    assert contact.phone == "+37061234567"

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': org.pk
    }))
    assert resp.status_code == 200
    assert contact.email in resp.text
    assert contact.phone in resp.text
    assert coordinator.get_full_name() in resp.text
    
    
@pytest.mark.django_db
def test_contact_create_for_non_registered_contact(app, representative_data):
    org = representative_data['organization']
    app.set_user(representative_data['coordinator'])

    form = app.get(reverse('contact-create', kwargs={
        'pk': org.pk
    })).forms['contact-form']

    form["contact_name"] = "Test Testeron"
    form['email'] = "user@test.com"
    form['phone'] = "+37061234567"
    form['position'] = "Tester"

    resp = form.submit()
    assert resp.status_code == 302

    contact = Contact.objects.first()
    assert contact.content_type == None
    assert contact.object_id == None
    assert contact.organization == org
    assert contact.contact_name == "Test Testeron"
    assert contact.position == "Tester"
    assert contact.email == "user@test.com"
    assert contact.phone == "+37061234567"

    resp = app.get(reverse('organization-contacts', kwargs={
        'pk': org.pk
    }))
    assert resp.status_code == 200
    assert contact.contact_name in resp.text
    assert contact.position in resp.text
    assert contact.email in resp.text
    assert contact.phone in resp.text


@pytest.mark.django_db
def test_contact_create_no_permission(app, representative_data):
    app.set_user(representative_data['manager'])
    resp = app.get(reverse('contact-create', kwargs={
        'pk': representative_data['organization'].pk
    }), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_contact_update_org(app, representative_data):
    app.set_user(representative_data['coordinator'])
    org = representative_data['organization']
    contact = Contact.objects.create(
        organization=org,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        email="old@test.com",
        phone="+37061234567"
    )

    form = app.get(reverse('contact-update', kwargs={
        'pk': org.pk,
        'contact_id': contact.pk
    })).forms['contact-form']

    form['email'] = "updated@test.com"
    form['phone'] = "+37067654321"

    resp = form.submit()
    assert resp.status_code == 302

    contact.refresh_from_db()
    assert contact.email == "updated@test.com"
    assert contact.phone == "+37067654321"


@pytest.mark.django_db
def test_contact_update_user(app, representative_data):
    coordinator = representative_data['coordinator']
    app.set_user(coordinator)
    org = representative_data['organization']
    contact = Contact.objects.create(
        organization=org,
        content_type=ContentType.objects.get_for_model(coordinator),
        object_id=coordinator.pk,
        email="old@test.com",
        phone="+37061234567",
        position="Tester",
    )
    form = app.get(reverse('contact-update', kwargs={
        'pk': org.pk,
        'contact_id': contact.pk
    })).forms['contact-form']

    form['email'] = "updated@test.com"

    resp = form.submit()
    assert resp.status_code == 302

    contact.refresh_from_db()
    assert contact.email == "updated@test.com"


@pytest.mark.django_db
def test_contact_delete(app, representative_data):
    app.set_user(representative_data['coordinator'])
    org = representative_data['organization']
    contact = Contact.objects.create(
        organization=org,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
    )
    url = reverse('organization-contacts', kwargs={
        'pk': org.pk
    })
    resp = app.get(url)
    resp = resp.click(linkid=f"delete-contact-{contact.pk}-btn")
    form = resp.forms['delete-form']
    resp = form.submit()

    assert resp.headers['location'] == url
    assert resp.status_code == 302
    c = Contact.objects.filter(pk=contact.pk)
    assert not c.exists()


@pytest.mark.django_db
def test_contact_delete_no_permission(app, representative_data):
    app.set_user(representative_data['manager'])  # Manager shouldn't have permission
    org = representative_data['organization']
    contact = Contact.objects.create(
        organization=org,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
    )

    resp = app.get(reverse('contact-delete', kwargs={
        'pk': org.pk,
        'contact_id': contact.pk
    }), expect_errors=True)

    assert resp.status_code == 403
    assert Contact.objects.count() == 1


class TestRepresentativeDeleteView:
    @pytest.mark.django_db
    def test_delete_representative(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)

        organization = OrganizationFactory()
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization.pk,
        )

        app.post(
            reverse("representative-delete", args=[organization.pk, representative.pk])
        )

        assert not Representative.objects.filter(pk=representative.pk).exists()

    @pytest.mark.django_db
    def test_remove_publisher_from_all_representative_organization_datasets(
        self, app: DjangoTestApp
    ) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)

        organization = OrganizationFactory()
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization.pk,
            organization=organization,
        )
        dataset = DatasetFactory(organization=organization, publisher=organization)

        app.post(
            reverse("representative-delete", args=[organization.pk, representative.pk])
        )

        dataset.refresh_from_db()
        assert dataset.publisher is None


class TestOrganizationApiKeysDeleteView:
    @pytest.mark.django_db
    def test_delete_api_client_if_spinta_request_successful(
        self, app: DjangoTestApp
    ) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)
        organization = OrganizationFactory()
        api_key = APIKeyFactory()

        with patch(
            "vitrina.orgs.views.OrganizationApiKeysDeleteView.spinta_delete_apikey",
            return_value=Mock(status_code=204),
        ) as api_delete_request_mock:
            app.post(
                reverse("organization-apikeys-delete", args=[organization.pk, api_key.pk]),
            )

            assert not ApiKey.objects.exists()
            api_delete_request_mock.assert_called_once()

    @pytest.mark.django_db
    def test_do_not_delete_api_client_if_spinta_request_unsuccessful(
        self, app: DjangoTestApp
    ) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)
        organization = OrganizationFactory()
        api_key = APIKeyFactory()

        with patch(
            "vitrina.orgs.views.OrganizationApiKeysDeleteView.spinta_delete_apikey",
            return_value=Mock(status_code=500),
        ) as api_delete_request_mock:
            app.post(
                reverse("organization-apikeys-delete", args=[organization.pk, api_key.pk]),
            )

            assert ApiKey.objects.exists()
            api_delete_request_mock.assert_called_once()
