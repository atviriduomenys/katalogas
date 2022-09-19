import pytest
from datetime import datetime

from django.core import mail
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.models import User


@pytest.fixture
def data_for_tabs():
    parent_organization = OrganizationFactory(slug="org1")
    organization = parent_organization.add_child(instance=OrganizationFactory.build(slug="org2"))
    dataset = DatasetFactory(organization=organization)
    representative = RepresentativeFactory(organization=organization)
    return {
        'parent': parent_organization,
        'organization': organization,
        'dataset': dataset,
        'representative': representative
    }


@pytest.mark.django_db
def test_organization_detail_tab(app: DjangoTestApp, data_for_tabs):
    resp = app.get(data_for_tabs["organization"].get_absolute_url())
    assert list(resp.context['ancestors']) == [data_for_tabs["parent"]]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Informacija"]


@pytest.mark.django_db
def test_organization_members_tab(app: DjangoTestApp, data_for_tabs):
    resp = app.get(reverse('organization-members', args=[data_for_tabs["organization"].pk]))
    assert list(resp.context['members']) == [data_for_tabs["representative"]]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Organizacijos nariai"]


@pytest.mark.django_db
def test_organization_dataset_tab(app: DjangoTestApp, data_for_tabs):
    resp = app.get(reverse('organization-datasets', args=[data_for_tabs["organization"].pk]))
    assert list(resp.context['object_list']) == [data_for_tabs["dataset"]]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Duomenų rinkiniai"]


@pytest.fixture
def organizations():
    organization1 = OrganizationFactory(
        slug="org1",
        title="Organization 1",
        created=datetime(2022, 8, 22, 10, 30),
        jurisdiction="Jurisdiction1"
    )
    organization2 = OrganizationFactory(
        slug="org2",
        title="Organization 2",
        created=datetime(2022, 10, 22, 10, 30),
        jurisdiction="Jurisdiction2"
    )
    organization3 = OrganizationFactory(
        slug="org3",
        title="Organization 3",
        created=datetime(2022, 9, 22, 10, 30),
        jurisdiction="Jurisdiction2"
    )
    return [organization1, organization2, organization3]


@pytest.mark.django_db
def test_search_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]


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
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]


@pytest.mark.django_db
def test_filter_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]
    assert resp.context['selected_jurisdiction'] is None
    assert resp.context['jurisdictions'] == [
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
        },
        {
            'title': 'Jurisdiction2',
            'query': "?jurisdiction=Jurisdiction2",
            'count': 0
        }
    ]


@pytest.mark.django_db
def test_filter_with_other_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=Jurisdiction2" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2]]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction2"
    assert resp.context['jurisdictions'] == [
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
    ]


@pytest.mark.django_db
def test_filter_with_non_existent_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=doesnotexist" % reverse('organization-list'))
    assert len(resp.context['object_list']) == 0
    assert resp.context['selected_jurisdiction'] == "doesnotexist"
    assert resp.context['jurisdictions'] == [
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
    ]


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
        {
            'title': 'Jurisdiction2',
            'query': "?q=1&jurisdiction=Jurisdiction2",
            'count': 0
        }
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
        role="manager",
        first_name="Manager",
        last_name="User",
        phone="861234567"
    )
    coordinator = User.objects.create_user(
        email="coordinator@gmail.com",
        password="coordinator123",
        role="coordinator",
        first_name="Coordinator",
        last_name="User",
        phone="869876543"
    )
    organization = OrganizationFactory()
    representative_manager = RepresentativeFactory(role="manager", organization=organization)
    representative_coordinator = RepresentativeFactory(role="coordinator", organization=organization)
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
    representative_data['manager'].refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert Representative.objects.filter(email="manager@gmail.com").count() == 1
    assert Representative.objects.filter(email="manager@gmail.com").first().first_name == \
           representative_data['manager'].first_name
    assert Representative.objects.filter(email="manager@gmail.com").first().last_name == \
           representative_data['manager'].last_name
    assert Representative.objects.filter(email="manager@gmail.com").first().phone == \
           representative_data['manager'].phone
    assert Representative.objects.filter(email="manager@gmail.com").first().organization == \
           representative_data['organization']
    assert Representative.objects.filter(email="manager@gmail.com").first().user == representative_data['manager']
    assert representative_data['manager'].role == 'coordinator'


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
    assert Representative.objects.filter(email="new@gmail.com").first().organization == \
           representative_data['organization']
    assert Representative.objects.filter(email="new@gmail.com").first().user is None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@gmail.com"]


@pytest.mark.django_db
def test_register_after_adding_representative(app: DjangoTestApp, representative_data):
    new_representative = RepresentativeFactory(
        email="new@gmail.com",
        organization=representative_data['organization']
    )
    form = app.get(reverse('register')).forms['register-form']
    form['first_name'] = "New"
    form['last_name'] = "User"
    form['email'] = "new@gmail.com"
    form['password1'] = "test123?"
    form['password2'] = "test123?"
    form['agree_to_terms'] = True
    resp = form.submit()
    new_representative.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('home')
    assert User.objects.filter(email='new@gmail.com').count() == 1
    assert User.objects.filter(email='new@gmail.com').first().role == new_representative.role
    assert User.objects.filter(email='new@gmail.com').first().organization == new_representative.organization
    assert new_representative.user == User.objects.filter(email='new@gmail.com').first()
    assert new_representative.first_name == User.objects.filter(email='new@gmail.com').first().first_name
    assert new_representative.last_name == User.objects.filter(email='new@gmail.com').first().last_name


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
    representative_data['manager'].refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('organization-members', kwargs={'pk': representative_data['organization'].pk})
    assert representative_data['representative_manager'].role == "coordinator"
    assert representative_data['manager'].role == "coordinator"

