import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs import forms
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization, Representative

from vitrina.users.models import User


@pytest.mark.django_db
def test_admin_add_publisher(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    organization = OrganizationFactory()
    app.set_user(admin)
    form = app.get(reverse('admin:vitrina_orgs_publisherorganization_add')).forms['publisherorganization_form']
    form['organization'] = organization.pk
    form.submit()
    assert Organization.objects.filter(publisher=True, pk=organization.pk).exists()


@pytest.mark.django_db
def test_admin_publisher_list_display(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    org = OrganizationFactory(title = 'title')
    for title in ['title1', 'title2', 'title3']:
        OrganizationFactory(title=title, publisher=True)
    app.set_user(admin)
    resp = app.get(reverse('admin:vitrina_orgs_publisherorganization_changelist'))
    assert [org.title for org in resp.context['cl'].result_list] == ['title1', 'title2', 'title3']
    assert org.title not in [org.title for org in resp.context['cl'].result_list]

@pytest.mark.django_db
def test_admin_publisher_update(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    publisher_org = OrganizationFactory(publisher=True)
    app.set_user(admin)
    form = app.get(reverse('admin:vitrina_orgs_publisherorganization_change', args=[publisher_org.pk])).forms['publisherorganization_form']
    assert True


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email="admin@gmail.com",
        password="test123"
    )

@pytest.fixture
def publisher_org():
    return OrganizationFactory(publisher=True)


@pytest.fixture
def creator_org():
    return OrganizationFactory(publisher=False)

@pytest.mark.django_db
def test_form_initial_load(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    app.set_user(admin_user)
    response = app.get(
        reverse('admin:vitrina_orgs_publisherorganization_change',
                args=[publisher_org.pk])
    )

    form = response.forms['publisherorganization_form']
    assert form['coordinator'].value == ''
    assert form['existing_creators'].value == ''
    assert form['removed_creators'].value == ''


@pytest.mark.django_db
def test_admin_publisher_add_new_creator(app, admin_user, publisher_org, monkeypatch):
    def mock_get_data_from_spinta(*args, **kwargs):
        return {
            '_data': [{
                'ja_pavadinimas': 'Test Organization',
                'ja_kodas': '123456789',
                'pilnas_adresas': 'Test Address 1'
            }]
        }

    existing_org = OrganizationFactory(company_code='123456789')
    for ds in ['tst-1', 'tst-2']:
        DatasetFactory(slug=ds, organization=existing_org)

    monkeypatch.setattr(forms, 'get_data_from_spinta', mock_get_data_from_spinta)
    app.set_user(admin_user)
    response = app.get(
        reverse('admin:vitrina_orgs_publisherorganization_change',
                args=[publisher_org.pk])
    )
    form = response.forms['publisherorganization_form']

    form.fields['creator'][0].options.append(('123456789', False, 'Test Organization'))
    form['creator'] = '123456789'
    response = form.submit()

    assert response.status_code == 302
    assert Representative.objects.filter(
        organization=publisher_org,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=existing_org.id
    ).exists()

    ds = Dataset.objects.filter(publisher=publisher_org)
    assert ds.count() == 2
    assert list(ds.values_list('slug', flat=True)) == ['tst-1', 'tst-2']

@pytest.mark.django_db
def test_admin_publisher_remove_creator(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    existing_org = OrganizationFactory()
    for ds in ['tst-1', 'tst-2']:
        DatasetFactory(slug=ds, organization=existing_org, publisher=publisher_org)
    Representative.objects.create(
        organization=publisher_org,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=existing_org.pk
    )

    ds_before = Dataset.objects.filter(publisher=publisher_org)
    assert ds_before.count() == 2
    assert list(ds_before.values_list('slug', flat=True)) == ['tst-1', 'tst-2']

    app.set_user(admin_user)
    form = app.get(
        reverse('admin:vitrina_orgs_publisherorganization_change',
                args=[publisher_org.pk])
    ).forms['publisherorganization_form']
    form['removed_creators'] = str(existing_org.id)
    response = form.submit()

    assert response.status_code == 302
    assert not Representative.objects.filter(
        organization=publisher_org,
        object_id=existing_org.id
    ).exists()

    ds = Dataset.objects.filter(publisher=publisher_org)
    assert ds.count() == 0
    assert list(ds.values_list('slug', flat=True)) == []


@pytest.mark.django_db
def test_admin_dataset_assign(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    datasets = [DatasetFactory() for _ in range(3)]

    app.set_user(admin_user)
    form = app.get(
        reverse('admin:vitrina_orgs_publisherorganization_change',
                args=[publisher_org.pk])
    ).forms['publisherorganization_form']

    form['datasets'] = [str(dataset.id) for dataset in datasets]
    response = form.submit()

    assert response.status_code == 302
    for dataset in datasets:
        assert Representative.objects.filter(
            organization=publisher_org,
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id=dataset.id
        ).exists()


@pytest.mark.django_db
def test_admin_dataset_remove(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    datasets = [DatasetFactory() for _ in range(3)]
    app.set_user(admin_user)
    for dataset in datasets:
        Representative.objects.create(
            organization=publisher_org,
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id=dataset.id
        )
    form = app.get(
        reverse('admin:vitrina_orgs_publisherorganization_change',
                args=[publisher_org.pk])
    ).forms['publisherorganization_form']
    form['datasets'] = [str(datasets[0].id), str(datasets[1].id)]
    response = form.submit()
    assert response.status_code == 302

    assert not Representative.objects.filter(
        organization=publisher_org,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=datasets[2].id
    ).exists()

    for dataset in datasets[:2]:
        assert Representative.objects.filter(
            organization=publisher_org,
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id=dataset.id
        ).exists()

