from datetime import datetime, date

import pytz
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse
from django_webtest import DjangoTestApp

import pytest
from factory.django import FileField
from filer.models import File
from reversion.models import Version
from webtest import Upload

from vitrina.classifiers.factories import CategoryFactory, FrequencyFactory
from vitrina.classifiers.factories import LicenceFactory
from vitrina.classifiers.models import Category
from vitrina.cms.factories import FilerFileFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory, DatasetGroupFactory
from vitrina.datasets.factories import MANIFEST
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.projects.factories import ProjectFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.users.factories import UserFactory, ManagerFactory
from vitrina.users.models import User

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.fixture
def dataset_detail_data():
    dataset = DatasetFactory()
    dataset_distribution = DatasetDistributionFactory(dataset=dataset)
    return {
        'dataset': dataset_distribution.dataset,
        'dataset_distribution': dataset_distribution
    }


@pytest.mark.django_db
def test_dataset_detail_without_tags(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(dataset_detail_data['dataset'].get_absolute_url())
    assert resp.context['tags'] == []


@pytest.mark.django_db
def test_dataset_detail_tags(app: DjangoTestApp, dataset_detail_data):
    dataset = DatasetFactory(tags=('tag-1', 'tag-2', 'tag-3'), status="HAS_DATA")
    resp = app.get(dataset.get_absolute_url())
    assert len(resp.context['tags']) == 3
    assert resp.context['tags'] == ['tag-1', 'tag-2', 'tag-3']


@pytest.mark.django_db
def test_dataset_detail_status(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(dataset_detail_data['dataset'].get_absolute_url())
    assert resp.context['status'] == "Atvertas"


@pytest.mark.django_db
def test_dataset_detail_resources(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(dataset_detail_data['dataset'].get_absolute_url())
    assert list(resp.context['resources']) == [dataset_detail_data['dataset_distribution']]


@pytest.mark.django_db
def test_distribution_preview(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(reverse('dataset-distribution-preview', kwargs={
        'dataset_id': dataset_detail_data['dataset'].pk,
        'distribution_id': dataset_detail_data['dataset_distribution'].pk
    }))
    assert resp.json == {'data': [['Column'], ['Value']]}


@pytest.fixture
def search_datasets():
    dataset1 = DatasetFactory(slug='ds1', published=timezone.localize(datetime(2022, 6, 1)))
    dataset1.set_current_language('en')
    dataset1.title = 'Dataset 1'
    dataset1.save()
    dataset1.set_current_language('lt')
    dataset1.title = "Duomenų rinkinys vienas"
    dataset1.save()

    dataset2 = DatasetFactory(slug='ds2', published=timezone.localize(datetime(2022, 8, 1)))
    dataset2.set_current_language('en')
    dataset2.title = 'Dataset 2'
    dataset2.save()
    dataset2.set_current_language('lt')
    dataset2.title = "Duomenų rinkinys du\"<'>\\"
    dataset2.save()

    dataset3 = DatasetFactory(slug='ds3', published=timezone.localize(datetime(2022, 7, 1)))
    dataset3.set_current_language('en')
    dataset3.title = 'Dataset 3'
    dataset3.save()
    dataset3.set_current_language('lt')
    dataset3.title = "Duomenų rinkinys trys"
    dataset3.save()
    return [dataset1, dataset2, dataset3]


@pytest.mark.haystack
def test_search_without_query(app: DjangoTestApp, search_datasets):
    resp = app.get(reverse('dataset-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]


@pytest.mark.haystack
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "doesnt-match"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == []


@pytest.mark.haystack
def test_search_with_query_that_matches_one(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "vienas"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_datasets[0].pk]


@pytest.mark.haystack
def test_search_with_query_that_matches_all(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "rinkinys"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]


@pytest.mark.haystack
def test_search_with_query_that_matches_all_with_english_title(app: DjangoTestApp, search_datasets):
    for dataset in search_datasets:
        dataset.set_current_language('en')
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "Dataset"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]


@pytest.mark.haystack
def test_search_with_query_containing_special_characters(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "du\"<'>\\"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_datasets[1].pk]


@pytest.fixture
def status_filter_data():
    dataset1 = DatasetFactory()
    dataset2 = DatasetFactory(status=Dataset.INVENTORED)
    return [dataset1, dataset2]


@pytest.mark.haystack
def test_status_filter_without_query(app: DjangoTestApp, status_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        status_filter_data[0].pk,
        status_filter_data[1].pk
    ]
    assert resp.context['selected_status'] is None


@pytest.mark.haystack
def test_status_filter_inventored(app: DjangoTestApp, status_filter_data):
    resp = app.get("%s?selected_facets=filter_status_exact:%s" % (
        reverse('dataset-list'),
        Dataset.INVENTORED
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [status_filter_data[1].pk]
    assert resp.context['selected_status'] == Dataset.INVENTORED


@pytest.fixture
def organization_filter_data():
    organization = OrganizationFactory()

    dataset1 = DatasetFactory(organization=organization, slug='ds1')
    dataset2 = DatasetFactory(organization=organization, slug='ds2')

    return {
        "organization": organization,
        "datasets": [dataset1, dataset2]
    }


@pytest.mark.haystack
def test_organization_filter_without_query(app: DjangoTestApp, organization_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        organization_filter_data["datasets"][0].pk,
        organization_filter_data['datasets'][1].pk
    ]
    assert resp.context['selected_organization'] == []


@pytest.mark.haystack
def test_organization_filter_with_organization(app: DjangoTestApp, organization_filter_data):
    resp = app.get("%s?selected_facets=organization_exact:%s" % (
        reverse("dataset-list"),
        organization_filter_data["organization"].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        organization_filter_data["datasets"][0].pk,
        organization_filter_data['datasets'][1].pk
    ]
    assert resp.context['selected_organization'][0] == str(organization_filter_data["organization"].pk)


@pytest.fixture
def category_filter_data():
    organization = OrganizationFactory()

    category1 = CategoryFactory(title='Cat 1')
    category2 = category1.add_child(
        instance=CategoryFactory.build(title='Cat 1.1'),
    )
    category3 = category1.add_child(
        instance=CategoryFactory.build(title='Cat 1.2'),
    )
    category4 = category2.add_child(
        instance=CategoryFactory.build(title='Cat 2.1'),
    )
    dataset_with_category1 = DatasetFactory(category=category1, slug="ds1", organization=organization)
    dataset_with_category2 = DatasetFactory(category=category2, slug="ds2", organization=organization)
    dataset_with_category3 = DatasetFactory(category=category3, slug="ds3", organization=organization)
    dataset_with_category4 = DatasetFactory(category=category4, slug="ds4", organization=organization)

    return {
        "categories": [category1, category2, category3, category4],
        "datasets": [
            dataset_with_category1,
            dataset_with_category2,
            dataset_with_category3,
            dataset_with_category4,
        ],
    }


@pytest.mark.haystack
def test_category_filter_without_query(app: DjangoTestApp, category_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert len(resp.context['object_list']) == 4
    assert resp.context['selected_categories'] == []


@pytest.mark.haystack
def test_category_filter_with_parent_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("dataset-list"),
        category_filter_data["categories"][0].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["datasets"][0].pk,
        category_filter_data["datasets"][1].pk,
        category_filter_data["datasets"][2].pk,
        category_filter_data["datasets"][3].pk
    ]
    assert resp.context['selected_categories'] == [str(category_filter_data["categories"][0].pk)]


@pytest.mark.haystack
def test_category_filter_with_middle_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("dataset-list"),
        category_filter_data["categories"][1].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["datasets"][1].pk,
        category_filter_data["datasets"][3].pk,
    ]
    assert resp.context['selected_categories'] == [
        str(category_filter_data["categories"][1].pk),
    ]


@pytest.mark.haystack
def test_category_filter_with_child_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("dataset-list"),
        category_filter_data["categories"][3].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["datasets"][3].pk,
    ]
    assert resp.context['selected_categories'] == [
        str(category_filter_data["categories"][3].pk),
    ]


@pytest.mark.haystack
def test_category_filter_with_parent_and_child_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get((
        '%s?'
        'selected_facets=category_exact:%s&'
        'selected_facets=category_exact:%s'
    ) % (
        reverse("dataset-list"),
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][3].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["datasets"][3].pk,
    ]
    assert resp.context['selected_categories'] == [
        str(category_filter_data["categories"][0].pk),
        str(category_filter_data["categories"][3].pk)
    ]

@pytest.mark.haystack
def test_data_group_filter_header_visible_if_data_groups_exist(
    app: DjangoTestApp,
):
    group = DatasetGroupFactory()
    dataset = DatasetFactory()
    dataset.groups.set([group])
    dataset.save()
    resp = app.get(reverse('dataset-list'))
    assert resp.html.find(id='data_group_filter_header')

@pytest.mark.haystack
def test_data_group_filter_header_not_visible_if_data_groups_do_not_exist(
    app: DjangoTestApp,
):
    dataset = DatasetFactory()
    resp = app.get(reverse('dataset-list'))
    assert not resp.html.find(id='data_group_filter_header')

@pytest.fixture
def datasets():
    dataset1 = DatasetFactory(tags=('tag1', 'tag2', 'tag3'), slug="ds1")
    dataset2 = DatasetFactory(tags=('tag3', 'tag4', 'tag5'), slug="ds2")

    return [dataset1, dataset2]


@pytest.mark.haystack
def test_tag_filter_without_query(app: DjangoTestApp, datasets):
    resp = app.get(reverse('dataset-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        datasets[0].pk, datasets[1].pk,
    ]
    assert [int(obj.pk) for obj in resp.context['object_list']] == [datasets[0].pk, datasets[1].pk]
    assert resp.context['selected_tags'] == []

@pytest.mark.haystack
def test_tag_filter_with_one_tag(app: DjangoTestApp, datasets):
    resp = app.get("%s?selected_facets=tags_exact:tag2" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [datasets[0].pk]
    assert resp.context['selected_tags'] == ['tag2']


@pytest.mark.haystack
def test_tag_filter_with_shared_tag(app: DjangoTestApp, datasets):
    resp = app.get("%s?selected_facets=tags_exact:tag3" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [datasets[0].pk, datasets[1].pk]
    assert resp.context['selected_tags'] == ['tag3']


@pytest.mark.haystack
def test_tag_filter_with_multiple_tags(app: DjangoTestApp, datasets):
    resp = app.get("%s?selected_facets=tags_exact:tag4&selected_facets=tags_exact:tag3" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [datasets[1].pk]
    assert resp.context['selected_tags'] == ['tag4', 'tag3']


@pytest.fixture
def frequency_filter_data():
    frequency = FrequencyFactory()
    organization = OrganizationFactory()

    dataset1 = DatasetFactory(frequency=frequency, organization=organization)
    dataset2 = DatasetFactory(frequency=frequency, organization=organization)

    return {
        "frequency": frequency,
        "datasets": [dataset1, dataset2]
    }


@pytest.mark.haystack
def test_frequency_filter_without_query(app: DjangoTestApp, frequency_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        frequency_filter_data["datasets"][0].pk,
        frequency_filter_data["datasets"][1].pk
    ]
    assert resp.context['selected_frequency'] is None


@pytest.mark.haystack
def test_frequency_filter_with_frequency(app: DjangoTestApp, frequency_filter_data):
    resp = app.get("%s?selected_facets=frequency_exact:%s" % (
        reverse("dataset-list"),
        frequency_filter_data["frequency"].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        frequency_filter_data["datasets"][0].pk,
        frequency_filter_data["datasets"][1].pk
    ]
    assert resp.context['selected_frequency'] == frequency_filter_data["frequency"].pk


@pytest.fixture
def date_filter_data():
    org = OrganizationFactory()
    dataset1 = DatasetFactory(organization=org, slug='ds1', published=timezone.localize(datetime(2022, 3, 1)))
    dataset2 = DatasetFactory(organization=org, slug='ds2', published=timezone.localize(datetime(2022, 2, 1)))
    dataset3 = DatasetFactory(organization=org, slug='ds3', published=timezone.localize(datetime(2021, 12, 1)))
    return [dataset1, dataset2, dataset3]


@pytest.mark.haystack
def test_date_filter_without_query(app: DjangoTestApp, date_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        date_filter_data[0].pk,
        date_filter_data[1].pk,
        date_filter_data[2].pk
    ]
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] is None


@pytest.mark.haystack
def test_date_filter_wit_date_from(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-02-10" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[0].pk]
    assert resp.context['selected_date_from'] == date(2022, 2, 10)
    assert resp.context['selected_date_to'] is None


@pytest.mark.haystack
def test_date_filter_with_date_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_to=2022-02-10" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[1].pk, date_filter_data[2].pk]
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] == date(2022, 2, 10)


@pytest.mark.haystack
def test_date_filter_with_dates_from_and_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[1].pk]
    assert resp.context['selected_date_from'] == date(2022, 1, 1)
    assert resp.context['selected_date_to'] == date(2022, 2, 10)


@pytest.mark.haystack
def test_dataset_filter_all(app: DjangoTestApp):
    organization = OrganizationFactory()
    category = CategoryFactory()
    frequency = FrequencyFactory()
    dataset_with_all_filters = DatasetFactory(
        status=Dataset.HAS_DATA,
        tags=('tag1', 'tag2', 'tag3'),
        published=timezone.localize(datetime(2022, 2, 9)),
        organization=organization,
        category=category,
        frequency=frequency
    )

    distribution = DatasetDistributionFactory()
    distribution.dataset = dataset_with_all_filters
    distribution.save()

    dataset_with_all_filters.set_current_language(settings.LANGUAGE_CODE)
    dataset_with_all_filters.slug = 'ds1'
    dataset_with_all_filters.save()

    resp = app.get(
        "%s?selected_facets=filter_status_exact:%s"
        "&selected_facets=organization_exact:%s&"
        "selected_facets=category_exact:%s&"
        "selected_facets=tags_exact:tag1&"
        "selected_facets=tags_exact:tag2&"
        "selected_facets=frequency_exact:%s"
        "&date_from=2022-01-01&"
        "date_to=2022-02-10" % (reverse("dataset-list"), Dataset.HAS_DATA, organization.pk, category.pk, frequency.pk))

    assert [int(obj.pk) for obj in resp.context['object_list']] == [dataset_with_all_filters.pk]
    assert resp.context['selected_status'] == Dataset.HAS_DATA
    assert resp.context['selected_organization'][0] == str(organization.pk)
    assert resp.context['selected_categories'] == [str(category.pk)]
    assert resp.context['selected_tags'] == ["tag1", "tag2"]
    assert resp.context['selected_frequency'] == frequency.pk
    assert resp.context['selected_date_from'] == date(2022, 1, 1)
    assert resp.context['selected_date_to'] == date(2022, 2, 10)


@pytest.mark.haystack
def test_dataset_filter_with_pages(app: DjangoTestApp):
    inventored_dataset = None
    for i in range(25):
        if i == 0:
            inventored_dataset = DatasetFactory(status=Dataset.INVENTORED)
        else:
            DatasetFactory()

    resp = app.get("%s?page=2" % (reverse('dataset-list')))
    assert 'page' not in resp.html.find(id="%s_id" % Dataset.INVENTORED).attrs['href']
    resp = resp.click(linkid="%s_id" % Dataset.INVENTORED)
    assert [int(obj.pk) for obj in resp.context['object_list']] == [inventored_dataset.pk]
    assert resp.context['selected_status'] == Dataset.INVENTORED


@pytest.fixture
def dataset_structure_data():
    organization = OrganizationFactory(slug="org", kind="gov")

    dataset1 = DatasetFactory(slug='ds2', organization=organization)
    dataset1.set_current_language(settings.LANGUAGE_CODE)
    dataset1.title = 'dataset1'
    dataset1.save()

    dataset2 = DatasetFactory(slug='ds3', organization=organization)
    dataset2.set_current_language(settings.LANGUAGE_CODE)
    dataset2.title = 'dataset2'
    dataset2.save()

    structure1 = DatasetStructureFactory(dataset=dataset1)
    structure2 = DatasetStructureFactory(dataset=dataset2, file=FileField(filename='file.csv', data=b'ab\0c'))
    return {
        'structure1': structure1,
        'structure2': structure2
    }


@pytest.mark.django_db
def test_with_structure(app: DjangoTestApp):
    dataset = DatasetFactory()
    dataset.current_structure = DatasetStructureFactory(dataset=dataset)
    dataset.save()
    resp = app.get(dataset.current_structure.get_absolute_url())
    assert resp.context['errors'] == []
    assert list(resp.context['manifest'].datasets) == ['datasets/gov/ivpk/adk']


@pytest.mark.django_db
def test_with_non_readable_structure(app: DjangoTestApp):
    dataset = DatasetFactory()
    dataset.current_structure = DatasetStructureFactory(
        dataset=dataset,
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=b'ab\0c')
        )
    )
    dataset.save()
    resp = app.get(dataset.current_structure.get_absolute_url())
    assert len(resp.context['errors']) > 0
    assert resp.context['manifest'] is None


@pytest.mark.django_db
def test_public_manager_filtering(app: DjangoTestApp):
    organization = OrganizationFactory(slug="org", kind="gov")

    DatasetFactory(is_public=False, organization=organization)
    DatasetFactory(deleted=True, deleted_on=timezone.localize(datetime.now()), organization=organization)
    DatasetFactory(deleted=True, deleted_on=None, organization=organization)
    DatasetFactory(deleted=None, deleted_on=None, organization=organization)
    DatasetFactory(deleted=None, deleted_on=None, organization=None)
    DatasetFactory(organization=organization)

    public_datasets = Dataset.public.all()
    assert public_datasets.count() == 2


@pytest.mark.django_db
def test_change_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    response = app.get(reverse('dataset-change', kwargs={'pk': dataset.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse('dataset-change', kwargs={'pk': dataset.id}))
    assert response.status_code == 302
    assert str(dataset.id) in response.location


@pytest.mark.django_db
def test_change_form_correct_login(app: DjangoTestApp):
    licence = LicenceFactory(is_default=True)
    frequency = FrequencyFactory(is_default=True)
    category = CategoryFactory()
    org = OrganizationFactory()
    dataset = DatasetFactory(
        published=timezone.localize(datetime(2022, 9, 7)),
        slug='test-dataset-slug',
        description='test description',
        category=category,
        licence=licence,
        frequency=frequency,
        organization=org
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset.manager = user
    form = app.get(reverse('dataset-change', kwargs={'pk': dataset.id})).forms['dataset-form']
    form['title'] = 'Edited title'
    form['description'] = 'edited dataset description'
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('dataset-detail', kwargs={'pk': dataset.id})
    assert dataset.title == 'Edited title'
    assert dataset.description == 'edited dataset description'
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.EDITED


@pytest.mark.django_db
def test_group_change_form_correct_login(app: DjangoTestApp):
    group = DatasetGroupFactory()
    dataset = DatasetFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('dataset-change', kwargs={'pk': dataset.id})).forms['dataset-form']
    form['groups'] = ['1']
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('dataset-detail', kwargs={'pk': dataset.id})
    assert dataset.groups.all().first() == group
    assert Version.objects.get_for_object(dataset).count() == 1


@pytest.mark.django_db
def test_click_edit_button(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(
        published=timezone.localize(datetime(2022, 9, 7)),
        slug='test-dataset-slug',
        organization=org
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset.manager = user
    response = app.get(reverse('dataset-detail', kwargs={'pk': dataset.id}))
    response.click(linkid='change_dataset')
    assert response.status_code == 200


@pytest.mark.django_db
def test_add_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    response = app.get(reverse('dataset-add', kwargs={'pk': org.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_add_form_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    org = OrganizationFactory()
    response = app.get(reverse('dataset-add', kwargs={'pk': org.id}))
    assert response.status_code == 302
    assert str(org.id) in response.location


@pytest.mark.django_db
def test_add_form_correct_login(app: DjangoTestApp):
    LicenceFactory(is_default=True)
    FrequencyFactory(is_default=True)
    category = CategoryFactory()
    org = OrganizationFactory(
        title="Org_title",
        created=timezone.localize(datetime(2022, 8, 22, 10, 30)),
        jurisdiction="Jurisdiction1",
        slug='test-org-slug',
        kind='test_org_kind'
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('dataset-add', kwargs={'pk': org.id})).forms['dataset-form']
    form['title'] = 'Added title'
    form['description'] = 'Added new dataset description'
    form['category'] = category.pk
    resp = form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Added title")
    assert added_dataset.count() == 1
    assert resp.status_code == 302
    assert str(added_dataset[0].id) in resp.url
    assert Version.objects.get_for_object(added_dataset.first()).count() == 1
    assert Version.objects.get_for_object(added_dataset.first()).first().revision.comment == Dataset.CREATED


@pytest.mark.haystack
@pytest.mark.django_db
def test_click_add_button(app: DjangoTestApp):
    org = OrganizationFactory(
        title="Org_title",
        created=timezone.localize(datetime(2022, 8, 22, 10, 30)),
        jurisdiction="Jurisdiction1",
        slug='test-org-slug',
        kind='test_org_kind'
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(reverse('organization-datasets', kwargs={'pk': org.id}))
    response.click(linkid='add_dataset')
    assert response.status_code == 200


@pytest.fixture
def dataset():
    organization = OrganizationFactory(slug="org", kind="gov")
    dataset1 = DatasetFactory(slug='ds2', organization=organization)
    dataset1.set_current_language('en')
    dataset1.title = 'dataset1'
    dataset1.save()
    dataset1.set_current_language('lt')
    dataset1.title = 'dataset1'
    dataset1.save()

    return dataset1


@pytest.mark.django_db
def test_translations_default_language(app: DjangoTestApp, dataset):
    default_language = dataset.get_current_language()
    assert default_language == 'lt'


@pytest.mark.django_db
def test_language_change(app: DjangoTestApp, dataset):
    dataset.set_current_language('en')
    current = dataset.get_current_language()
    assert current == 'en'


@pytest.mark.django_db
def test_dataset_add_form_initial_values(app: DjangoTestApp):
    default_licence = LicenceFactory(is_default=True)
    default_frequency = FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('dataset-add', kwargs={'pk': organization.id})).forms['dataset-form']
    assert form['licence'].value == str(default_licence.pk)
    assert form['frequency'].value == str(default_frequency.pk)


@pytest.mark.django_db
def test_dataset_history_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    app.set_user(user)
    resp = app.get(reverse('dataset-history', args=[dataset.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dataset_history_view_with_permission(app: DjangoTestApp):
    user = ManagerFactory(is_staff=True)
    dataset = DatasetFactory(organization=user.organization)
    app.set_user(user)

    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms['dataset-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit().follow()
    resp = resp.click(linkid="history-tab")
    assert resp.context['detail_url_name'] == 'dataset-detail'
    assert resp.context['history_url_name'] == 'dataset-history'
    assert len(resp.context['history']) == 1
    assert resp.context['history'][0]['action'] == "Redaguota"
    assert resp.context['history'][0]['user'] == user


@pytest.mark.django_db
def test_dataset_structure_import_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()

    app.set_user(user)
    url = reverse('dataset-structure-import', args=[dataset.pk])
    resp = app.get(url, expect_errors=True)

    assert resp.status_code == 403


@pytest.mark.django_db
def test_dataset_structure_import_not_standardized(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()

    app.set_user(user)
    resp = app.get(reverse('dataset-structure-import', args=[dataset.pk]))
    form = resp.forms['dataset-structure-form']
    form['file'] = Upload('manifest.csv', b'Column\nValue')
    form.submit()

    dataset.refresh_from_db()
    structure = DatasetStructure.objects.get(dataset=dataset)
    assert dataset.current_structure == structure
    assert File.objects.count() == 1
    assert structure.file.original_filename == "manifest.csv"


@pytest.mark.django_db
def test_dataset_structure_import_standardized(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()

    app.set_user(user)
    resp = app.get(reverse('dataset-structure-import', args=[dataset.pk]))
    form = resp.forms['dataset-structure-form']
    form['file'] = Upload('file.csv', MANIFEST.encode())
    form.submit()

    dataset.refresh_from_db()
    structure = DatasetStructure.objects.get(dataset=dataset)
    assert dataset.current_structure == structure
    assert File.objects.count() == 1
    assert structure.file.original_filename == "file.csv"


@pytest.mark.django_db
def test_dataset_members_view_bad_login(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    user = UserFactory()
    app.set_user(user)
    url = reverse('dataset-members', kwargs={
        'pk': representative.object_id,
    })
    response = app.get(url, expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_dataset_members_view_no_login(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(reverse('dataset-members', kwargs={'pk': dataset.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_dataset_members_create_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse('dataset-members', kwargs={'pk': dataset.pk})

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid="add-member-btn")

    form = resp.forms['representative-form']
    form['email'] = 'test@example.com'
    form['role'] = Representative.MANAGER
    resp = form.submit()

    assert resp.headers['location'] == url

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email='test@example.com',
    )
    assert rep.role == Representative.MANAGER
    assert rep.user is None

    assert len(mail.outbox) == 1
    assert '/register/' in mail.outbox[0].body


@pytest.mark.django_db
def test_dataset_members_add_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse('dataset-members', kwargs={'pk': dataset.pk})
    user = UserFactory(email='test@example.com')
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid="add-member-btn")

    form = resp.forms['representative-form']
    form['email'] = 'test@example.com'
    form['role'] = Representative.MANAGER
    resp = form.submit()

    assert resp.headers['location'] == url

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email='test@example.com',
    )
    assert rep.user == user
    assert rep.role == Representative.MANAGER

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_dataset_members_update_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse('dataset-members', kwargs={'pk': dataset.pk})

    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid=f"update-member-{manager.pk}-btn")

    form = resp.forms['representative-form']
    form['role'] = Representative.MANAGER
    resp = form.submit()

    assert resp.headers['location'] == url

    manager.refresh_from_db()
    assert manager.role == Representative.MANAGER

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_dataset_members_delete_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse('dataset-members', kwargs={'pk': dataset.pk})

    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid=f"delete-member-{manager.pk}-btn")

    form = resp.forms['delete-form']
    resp = form.submit()

    assert resp.headers['location'] == url

    qs = Representative.objects.filter(
        content_type=ct,
        object_id=dataset.id,
        user=manager.user,
    )
    assert not qs.exists()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_add_project_with_permission(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    dataset = DatasetFactory()
    app.set_user(user)
    resp = app.get(reverse('dataset-project-add', kwargs={'pk': dataset.pk}))
    form = resp.forms['dataset-add-project-form']
    form['projects'] = (project.pk,)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('dataset-projects', kwargs={'pk': dataset.pk})
    assert project.datasets.all().first() == dataset


@pytest.mark.django_db
def test_add_project_with_no_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    app.set_user(user)
    resp = app.get(reverse('dataset-project-add', kwargs={'pk': dataset.pk}), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_remove_project_no_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory()
    dataset = DatasetFactory()
    project.datasets.add(dataset)
    assert project.datasets.all().count() == 1

    app.set_user(user)

    resp = app.get(reverse('dataset-project-remove', kwargs={'pk': dataset.pk, 'project_id': project.pk}),
                   expect_errors=True)

    assert resp.status_code == 302


@pytest.mark.django_db
def test_remove_project_with_permission(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    dataset = DatasetFactory()
    url = reverse('dataset-projects', kwargs={'pk': dataset.pk})

    project.datasets.add(dataset)
    assert project.datasets.all().count() == 1

    app.set_user(user)

    resp = app.get(url)
    resp = resp.click(linkid=f"remove-project-{project.pk}-btn")

    form = resp.forms['delete-form']
    resp = form.submit()

    assert resp.headers['location'] == url
    assert project.datasets.all().count() == 0


@pytest.mark.haystack
def test_dataset_stats_view_no_login_with_query(app: DjangoTestApp,
                                                category_filter_data: dict[str, list[Category]]):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("dataset-list"),
        category_filter_data["categories"][1].pk
    ))
    old_object_list = resp.context['object_list']
    resp = resp.click(linkid="Dataset-status-stats")

    assert resp.status_code == 200
    assert resp.context['dataset_count'] == len(old_object_list)


@pytest.mark.haystack
def test_dataset_jurisdictions(app: DjangoTestApp):
    parent_org = OrganizationFactory()
    child_org1 = parent_org.add_child(
        instance=OrganizationFactory.build(title='org-test-1')
    )
    child_org2 = parent_org.add_child(
        instance=OrganizationFactory.build(title='org-test-2')
    )
    DatasetFactory(organization=parent_org)
    DatasetFactory(organization=child_org1)
    DatasetFactory(organization=child_org1)
    DatasetFactory(organization=child_org2)
    DatasetFactory(organization=child_org2)

    resp = app.get(reverse("dataset-list"))
    jurisdictions = resp.context['jurisdiction_facet']
    resp = resp.click(linkid="dataset-stats-supervisor")

    dataset_count = 0
    for org in jurisdictions:
        if dataset_count < org.get('count'):
            dataset_count = org.get('count')

    assert resp.context['jurisdictions'] == jurisdictions
    assert resp.context['max_count'] == dataset_count
    assert len(resp.context['jurisdictions']) == 1
    assert dataset_count == 5

@pytest.mark.haystack
def test_org_dataset_url_is_hidden_for_anon_user(app: DjangoTestApp):
    resp = app.get(reverse('dataset-list'))
    assert not resp.html.find(id='org-dataset-url')

@pytest.mark.haystack
def test_manager_dataset_url_is_hidden_for_anon_user(app: DjangoTestApp):
    resp = app.get(reverse('dataset-list'))
    assert not resp.html.find(id='manager-dataset-url')

@pytest.mark.haystack
def test_org_dataset_url_is_hidden_for_normal_user(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    assert not resp.html.find(id='org-dataset-url')

@pytest.mark.haystack
def test_manager_dataset_url_is_hidden_for_normal_user(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    assert not resp.html.find(id='manager-dataset-url')

@pytest.mark.haystack
def test_org_dataset_url_is_hidden_for_coordinator_if_no_datasets(app: DjangoTestApp):
    org = OrganizationFactory()
    user = User.objects.create_user(email="test@test.com", password="test123", organization=org)
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    assert not resp.html.find(id='org-dataset-url')

@pytest.mark.haystack
def test_manager_dataset_url_is_hidden_for_manager_if_no_datasets(app: DjangoTestApp):
    org = OrganizationFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.MANAGER,
    )
    app.set_user(rep.user)
    resp = app.get(reverse('dataset-list'))
    assert not resp.html.find(id='manager-dataset-url')

@pytest.mark.haystack
def test_org_dataset_url_is_shown_for_coordinator(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    user = User.objects.create_user(email="test@test.com", password="test123", organization=org)
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    assert resp.html.find(id='org-dataset-url')

@pytest.mark.haystack
def test_manager_dataset_url_is_shown_for_manager(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    ct = ContentType.objects.get_for_model(Dataset)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.MANAGER,
    )
    app.set_user(rep.user)
    resp = app.get(reverse('dataset-list'))
    assert resp.html.find(id='manager-dataset-url')

@pytest.mark.haystack
def test_org_datasets_are_shown_for_coordinator(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(title='testt', organization=org)
    user = User.objects.create_user(email="test@test.com", password="test123", organization=org)
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    resp = resp.click(linkid='org-dataset-url')
    assert [int(obj.pk) for obj in resp.context['object_list']] == [dataset.pk]

@pytest.mark.haystack
def test_manager_datasets_are_shown_for_manager(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    ct = ContentType.objects.get_for_model(Dataset)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.MANAGER,
    )
    app.set_user(rep.user)
    resp = app.get(reverse('dataset-list'))
    resp = resp.click(linkid='manager-dataset-url')
    assert [int(obj.pk) for obj in resp.context['object_list']] == [dataset.pk]

@pytest.mark.haystack
def test_datasets_from_multiple_orgs_are_shown_for_manager(app: DjangoTestApp):
    org = OrganizationFactory()
    org2 = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    dataset2= DatasetFactory(organization=org2)
    ct = ContentType.objects.get_for_model(Dataset)
    user = User.objects.create_user(email="test@test.com", password="test123")
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.MANAGER,
        user=user
    )
    rep2 = RepresentativeFactory(
        content_type=ct,
        object_id=org2.pk,
        role=Representative.MANAGER,
        user=user
    )
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    resp = resp.click(linkid='manager-dataset-url')
    assert [int(obj.pk) for obj in resp.context['object_list']] == [dataset.pk, dataset2.pk]