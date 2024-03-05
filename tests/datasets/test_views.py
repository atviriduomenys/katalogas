from datetime import datetime, date, timedelta

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
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory, DatasetGroupFactory, AttributionFactory, \
    DatasetAttributionFactory, TypeFactory, DataServiceTypeFactory, DataServiceSpecTypeFactory, RelationFactory, \
    DatasetRelationFactory
from vitrina.datasets.factories import MANIFEST
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan, PlanDataset
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
    assert resp.context['tags'] == [{'name': 'tag-1', 'pk': dataset.tags.get(name="tag-1").pk},
                                    {'name': 'tag-2', 'pk': dataset.tags.get(name="tag-2").pk},
                                    {'name': 'tag-3', 'pk': dataset.tags.get(name="tag-3").pk}]


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
    assert resp.json == {'data': [['Column'], [['Value']]]}


@pytest.fixture
def search_datasets():
    cat_parent1 = CategoryFactory(title='parent1')
    cat_parent2 = CategoryFactory(title='parent2')
    cat_child = cat_parent1.add_child(
        instance=CategoryFactory.build(title='child1'),
    )
    dataset1 = DatasetFactory(slug='ds1', published=timezone.localize(datetime(2022, 6, 1)),
                              tags=('test_tag_1', 'test_tag_2'))
    dataset1.category.add(cat_parent1)
    dataset1.set_current_language('en')
    dataset1.title = 'Dataset 1'
    dataset1.description = 'Description 1'
    dataset1.save()
    dataset1.set_current_language('lt')
    dataset1.title = "Duomenų rinkinys vienas"
    dataset1.description = 'test_lt_desc 1'
    dataset1.save()

    dataset2 = DatasetFactory(slug='ds2', published=timezone.localize(datetime(2022, 8, 1)),
                              tags=('test_tag_2', 'test_tag_3'))
    dataset2.category.add(cat_parent2)
    dataset2.set_current_language('en')
    dataset2.title = 'Dataset 2'
    dataset2.description = 'Description 2'
    dataset2.save()
    dataset2.set_current_language('lt')
    dataset2.title = "Duomenų rinkinys du\"<'>\\"
    dataset2.description = 'test_lt_desc 2'
    dataset2.save()

    dataset3 = DatasetFactory(slug='ds3', published=timezone.localize(datetime(2022, 7, 1)),
                              tags=('test_tag_4', 'test_tag_5'))
    dataset3.category.add(cat_child)
    dataset3.set_current_language('en')
    dataset3.title = 'Dataset 3'
    dataset3.description = 'Description 3'
    dataset3.save()
    dataset3.set_current_language('lt')
    dataset3.title = "Duomenų rinkinys trys"
    dataset3.description = 'test_lt_desc 3'
    dataset3.save()
    return [dataset1, dataset2, dataset3]


@pytest.mark.haystack
def test_dataset_list_view_anon_user_with_datasets(app: DjangoTestApp):
    DatasetFactory()
    DatasetFactory()
    DatasetFactory()
    resp = app.get(reverse('dataset-list'))
    assert len(resp.context['object_list']) == 3


@pytest.mark.haystack
def test_dataset_list_view_anon_user_without_datasets(app: DjangoTestApp):
    resp = app.get(reverse('dataset-list'))
    assert len(resp.context['object_list']) == 0


@pytest.mark.haystack
def test_dataset_list_view_all_shown_for_staff(app: DjangoTestApp):
    org1 = OrganizationFactory()
    org2 = OrganizationFactory()
    DatasetFactory(organization=org1, is_public=False)
    DatasetFactory(organization=org1)
    DatasetFactory(organization=org2)
    DatasetFactory(organization=org2, is_public=False)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    assert len(resp.context['object_list']) == 4


@pytest.mark.haystack
def test_dataset_list_view_public_shown_for_regular_user(app: DjangoTestApp):
    org1 = OrganizationFactory()
    org2 = OrganizationFactory()
    DatasetFactory(organization=org1, is_public=False)
    DatasetFactory(organization=org1)
    DatasetFactory(organization=org2)
    DatasetFactory(organization=org2, is_public=False)
    user = UserFactory()
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    assert len(resp.context['object_list']) == 2


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
    DatasetFactory(organization=org)
    user = User.objects.create_user(email="test@test.com", password="test123", organization=org)
    app.set_user(user)
    resp = app.get(reverse('dataset-list'))
    assert resp.html.find(id='org-dataset-url')


@pytest.mark.haystack
def test_manager_dataset_url_is_shown_for_manager(app: DjangoTestApp):
    org = OrganizationFactory()
    DatasetFactory(organization=org)
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
    dataset2 = DatasetFactory(organization=org2)
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
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([dataset.pk, dataset2.pk])


@pytest.mark.haystack
def test_search_without_query(app: DjangoTestApp, search_datasets):
    resp = app.get(reverse('dataset-list'))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[1].pk,
        search_datasets[2].pk,
        search_datasets[0].pk
    ])


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
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[1].pk,
        search_datasets[2].pk,
        search_datasets[0].pk
    ])


@pytest.mark.haystack
def test_search_with_query_that_matches_all_with_english_title(app: DjangoTestApp, search_datasets):
    for dataset in search_datasets:
        dataset.set_current_language('en')
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "Dataset"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[1].pk,
        search_datasets[2].pk,
        search_datasets[0].pk
    ])


@pytest.mark.haystack
def test_search_with_query_that_matches_all_description(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "test_lt_desc"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[0].pk,
        search_datasets[1].pk,
        search_datasets[2].pk,
    ])


@pytest.mark.haystack
def test_search_with_query_that_matches_all_with_english_description(app: DjangoTestApp, search_datasets):
    for dataset in search_datasets:
        dataset.set_current_language('en')
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "Description"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[0].pk,
        search_datasets[1].pk,
        search_datasets[2].pk,
    ])


@pytest.mark.haystack
def test_search_with_query_that_matches_child_category(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "child1"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[2].pk,
    ])


@pytest.mark.haystack
def test_search_with_query_that_matches_category_and_parent_category(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "parent1"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[0].pk,
        search_datasets[2].pk,
    ])


@pytest.mark.haystack
def test_search_with_query_that_matches_tag_of_one_dataset(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "test_tag_1"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[0].pk,
    ])


@pytest.mark.haystack
def test_search_with_query_that_matches_tag_of_two_datasets(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "test_tag_2"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        search_datasets[0].pk,
        search_datasets[1].pk,
    ])


@pytest.fixture
def status_filter_data():
    dataset1 = DatasetFactory()
    dataset2 = DatasetFactory(status=Dataset.INVENTORED)
    return [dataset1, dataset2]


@pytest.mark.haystack
def test_status_filter_without_query(app: DjangoTestApp, status_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        status_filter_data[0].pk,
        status_filter_data[1].pk
    ])
    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['status'].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_status_filter_inventored(app: DjangoTestApp, status_filter_data):
    resp = app.get("%s?selected_facets=status_exact:%s" % (
        reverse('dataset-list'),
        Dataset.INVENTORED
    ))

    objects = [int(obj.pk) for obj in resp.context['object_list']]
    assert objects == [status_filter_data[1].pk]

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['status'].items() if i.selected]
    assert selected == [Dataset.INVENTORED]


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
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        organization_filter_data["datasets"][0].pk,
        organization_filter_data['datasets'][1].pk
    ])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['organization'].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_organization_filter_with_organization(app: DjangoTestApp, organization_filter_data):
    resp = app.get("%s?selected_facets=organization_exact:%s" % (
        reverse("dataset-list"),
        organization_filter_data["organization"].pk
    ))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        organization_filter_data["datasets"][0].pk,
        organization_filter_data['datasets'][1].pk
    ])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['organization'].items() if i.selected]
    assert selected == [str(organization_filter_data["organization"].pk)]


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
    dataset_with_category1 = DatasetFactory(slug="ds1", organization=organization)
    dataset_with_category1.category.add(category1)
    dataset_with_category1.save()
    dataset_with_category2 = DatasetFactory(slug="ds2", organization=organization)
    dataset_with_category2.category.add(category2)
    dataset_with_category2.save()
    dataset_with_category3 = DatasetFactory(slug="ds3", organization=organization)
    dataset_with_category3.category.add(category3)
    dataset_with_category3.save()
    dataset_with_category4 = DatasetFactory(slug="ds4", organization=organization)
    dataset_with_category4.category.add(category4)
    dataset_with_category4.save()

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

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['category'].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_category_filter_with_parent_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("dataset-list"),
        category_filter_data["categories"][0].pk
    ))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        category_filter_data["datasets"][0].pk,
        category_filter_data["datasets"][1].pk,
        category_filter_data["datasets"][2].pk,
        category_filter_data["datasets"][3].pk
    ])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['category'].items() if i.selected]
    assert selected == [str(category_filter_data["categories"][0].pk)]


@pytest.mark.haystack
def test_category_filter_with_middle_category(
        app: DjangoTestApp,
        category_filter_data: dict[str, list[Category]],
):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("dataset-list"),
        category_filter_data["categories"][1].pk
    ))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        category_filter_data["datasets"][1].pk,
        category_filter_data["datasets"][3].pk,
    ])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['category'].items() if i.selected]
    assert selected == [str(category_filter_data["categories"][1].pk)]


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

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['category'].items() if i.selected]
    assert selected == [str(category_filter_data["categories"][3].pk)]


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

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['category'].items() if i.selected]
    assert sorted(selected) == sorted([
        str(category_filter_data["categories"][0].pk),
        str(category_filter_data["categories"][3].pk)
    ])


@pytest.mark.skip
@pytest.mark.haystack
def test_data_group_filter_header_visible_if_data_groups_exist(
        app: DjangoTestApp,
):
    group = DatasetGroupFactory()
    category = CategoryFactory()
    category.groups.add(group)
    dataset = DatasetFactory()
    dataset.category.add(category)
    dataset.save()
    resp = app.get(reverse('dataset-list'))
    assert resp.html.find(id='data_group_filter_header')


@pytest.mark.skip
@pytest.mark.haystack
def test_data_group_filter_header_not_visible_if_data_groups_do_not_exist(
        app: DjangoTestApp,
):
    DatasetFactory()
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
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        datasets[0].pk, datasets[1].pk,
    ])
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([datasets[0].pk, datasets[1].pk])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['tags'].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_tag_filter_with_one_tag(app: DjangoTestApp, datasets):
    tag_id = datasets[0].tags.get(name="tag2").pk
    resp = app.get("%s?selected_facets=tags_exact:%s" % (reverse("dataset-list"), tag_id))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [datasets[0].pk]

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['tags'].items() if i.selected]
    assert selected == [str(tag_id)]


@pytest.mark.haystack
def test_tag_filter_with_shared_tag(app: DjangoTestApp, datasets):
    tag_id = datasets[0].tags.get(name="tag3").pk
    resp = app.get("%s?selected_facets=tags_exact:%s" % (reverse("dataset-list"), tag_id))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([datasets[0].pk, datasets[1].pk])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['tags'].items() if i.selected]
    assert selected == [str(tag_id)]


@pytest.mark.haystack
def test_tag_filter_with_multiple_tags(app: DjangoTestApp, datasets):
    tag_id_1 = datasets[1].tags.get(name="tag3").pk
    tag_id_2 = datasets[1].tags.get(name="tag4").pk
    resp = app.get("%s?selected_facets=tags_exact:%s&selected_facets=tags_exact:%s" % (
        reverse("dataset-list"), tag_id_1, tag_id_2))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [datasets[1].pk]

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['tags'].items() if i.selected]
    assert sorted(selected) == sorted([str(tag_id_1), str(tag_id_2)])


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
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        frequency_filter_data["datasets"][0].pk,
        frequency_filter_data["datasets"][1].pk
    ])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['frequency'].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_frequency_filter_with_frequency(app: DjangoTestApp, frequency_filter_data):
    resp = app.get("%s?selected_facets=frequency_exact:%s" % (
        reverse("dataset-list"),
        frequency_filter_data["frequency"].pk
    ))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        frequency_filter_data["datasets"][0].pk,
        frequency_filter_data["datasets"][1].pk
    ])

    filters = {f.name: f for f in resp.context['filters']}
    selected = [i.value for i in filters['frequency'].items() if i.selected]
    assert selected == [frequency_filter_data["frequency"].pk]


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
    assert resp.context['form'].cleaned_data['date_from'] is None
    assert resp.context['form'].cleaned_data['date_to'] is None


@pytest.mark.haystack
def test_date_filter_wit_date_from(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-02-10" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[0].pk]
    assert resp.context['form'].cleaned_data['date_from'] == date(2022, 2, 10)
    assert resp.context['form'].cleaned_data['date_to'] is None


@pytest.mark.haystack
def test_date_filter_with_date_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_to=2022-02-10" % reverse("dataset-list"))
    assert sorted([int(obj.pk) for obj in resp.context['object_list']]) == sorted([
        date_filter_data[1].pk,
        date_filter_data[2].pk
    ])
    assert resp.context['form'].cleaned_data['date_from'] is None
    assert resp.context['form'].cleaned_data['date_to'] == date(2022, 2, 10)


@pytest.mark.haystack
def test_date_filter_with_dates_from_and_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[1].pk]
    assert resp.context['form'].cleaned_data['date_from'] == date(2022, 1, 1)
    assert resp.context['form'].cleaned_data['date_to'] == date(2022, 2, 10)


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
        frequency=frequency
    )
    dataset_with_all_filters.category.add(category)

    distribution = DatasetDistributionFactory()
    distribution.dataset = dataset_with_all_filters
    distribution.save()

    dataset_with_all_filters.set_current_language(settings.LANGUAGE_CODE)
    dataset_with_all_filters.slug = 'ds1'
    dataset_with_all_filters.save()

    tag_id_1 = dataset_with_all_filters.tags.get(name="tag1").pk
    tag_id_2 = dataset_with_all_filters.tags.get(name="tag2").pk

    resp = app.get(reverse("dataset-list") + '?' + (
        f"selected_facets=status_exact:{Dataset.HAS_DATA}&"
        f"selected_facets=organization_exact:{organization.pk}&"
        f"selected_facets=category_exact:{category.pk}&"
        f"selected_facets=tags_exact:{tag_id_1}&"
        f"selected_facets=tags_exact:{tag_id_2}&"
        f"selected_facets=frequency_exact:{frequency.pk}&"
        "date_from=2022-01-01&"
        "date_to=2022-02-10"
    ))

    objects = [int(obj.pk) for obj in resp.context['object_list']]
    assert objects == [dataset_with_all_filters.pk]

    selected = _get_selected(resp.context)
    assert selected == {
        'status': Dataset.HAS_DATA,
        'organization': str(organization.pk),
        'category': str(category.pk),
        'tags': [str(tag_id_1), str(tag_id_2)],
        'frequency': frequency.pk,
        'published': [
            (2022, 'Y'),
            (2022, 1, 'Q'),
            (2022, 2, 'M'),
        ],
    }


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

    objects = [int(obj.pk) for obj in resp.context['object_list']]
    assert objects == [inventored_dataset.pk]

    selected = _get_selected(resp.context)
    assert selected['status'] == Dataset.INVENTORED


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
        licence=licence,
        frequency=frequency,
        organization=org
    )
    dataset.category.add(category)
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
    resp = form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Added title")
    assert added_dataset.count() == 2
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
    assert rep.has_api_access is False
    assert rep.apikey_set.count() == 0

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
    assert rep.user.organization == dataset.organization
    assert rep.role == Representative.MANAGER
    assert rep.has_api_access is False
    assert rep.apikey_set.count() == 0

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_member_subscription(app: DjangoTestApp):
    subscriptions_before = Subscription.objects.all()
    assert len(subscriptions_before) == 0

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
    form['subscribe'] = True
    resp = form.submit()

    assert resp.headers['location'] == url

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email='test@example.com',
    )
    assert rep.user == user
    assert rep.user.organization == dataset.organization
    assert rep.role == Representative.MANAGER
    assert rep.has_api_access is False
    assert rep.apikey_set.count() == 0

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['test@example.com']

    subscriptions = Subscription.objects.all()
    assert len(subscriptions) == 1
    assert subscriptions[0].sub_type == Subscription.DATASET


@pytest.mark.django_db
def test_dataset_members_create_member_with_api_access(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    user = UserFactory(email='test@example.com')
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)
    resp = app.get(reverse('dataset-members', kwargs={'pk': dataset.pk}))
    resp = resp.click(linkid="add-member-btn")

    form = resp.forms['representative-form']
    form['email'] = 'test@example.com'
    form['role'] = Representative.MANAGER
    form['has_api_access'] = True
    form.submit()

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email='test@example.com',
    )
    assert rep.user == user
    assert rep.has_api_access is True
    assert rep.apikey_set.count() == 1


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
    assert manager.user.organization == dataset.organization

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_dataset_members_update_with_api_access(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)
    resp = app.get(reverse('dataset-members', kwargs={'pk': dataset.pk}))
    resp = resp.click(linkid=f"update-member-{coordinator.pk}-btn")

    form = resp.forms['representative-form']
    form['has_api_access'] = True
    form.submit()

    coordinator.refresh_from_db()
    assert coordinator.has_api_access is True
    assert coordinator.apikey_set.count() == 1


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
    # old_object_list = resp.context['object_list']
    # resp = resp.click(linkid="Dataset-stats-status")

    assert resp.status_code == 200
    # assert resp.context['dataset_count'] == len(old_object_list)


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
    filters = {f.name: f for f in resp.context['filters']}
    jurisdictions = list(filters['jurisdiction'].items())
    # resp = resp.click(linkid="dataset-stats-supervisor")

    dataset_count = 0
    for org in jurisdictions:
        if dataset_count < org.count:
            dataset_count = org.count

    # assert resp.context['jurisdictions'] == jurisdictions
    # assert resp.context['max_count'] == dataset_count
    # assert len(resp.context['jurisdictions']) == 1
    # assert dataset_count == 5
    assert resp.status_code == 200


@pytest.mark.django_db
def test_dataset_resource_create_button(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    resp = app.get(dataset.get_absolute_url())
    resp = resp.click(linkid="add_resource")
    assert resp.request.path == reverse('resource-add', args=[dataset.pk])


@pytest.mark.django_db
def test_dataset_assign_new_category_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    group = DatasetGroupFactory()
    category = CategoryFactory()
    category.groups.add(group)

    dataset = DatasetFactory()
    resp = app.get(reverse('assign-category', args=[dataset.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dataset_assign_new_category(csrf_exempt_django_app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    csrf_exempt_django_app.set_user(user)

    group = DatasetGroupFactory()
    category1 = CategoryFactory()
    category1.groups.add(group)
    category2 = CategoryFactory()
    category2.groups.add(group)
    category3 = CategoryFactory()
    category3.groups.add(group)

    dataset = DatasetFactory()
    resp = csrf_exempt_django_app.post(reverse('assign-category', args=[dataset.pk]), {
        'category': [category1.pk, category2.pk]
    })
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert list(dataset.category.order_by('pk')) == [category1, category2]


@pytest.mark.django_db
def test_dataset_change_category(csrf_exempt_django_app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    csrf_exempt_django_app.set_user(user)

    group = DatasetGroupFactory()
    category1 = CategoryFactory()
    category1.groups.add(group)
    category2 = CategoryFactory()
    category2.groups.add(group)
    category3 = CategoryFactory()
    category3.groups.add(group)

    dataset = DatasetFactory()
    dataset.category.add(category1)
    dataset.category.add(category2)

    resp = csrf_exempt_django_app.post(reverse('assign-category', args=[dataset.pk]), {
        'category': [category3.pk]
    })
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert list(dataset.category.all()) == [category3]


@pytest.mark.django_db
def test_dataset_create_attribution_with_organization_and_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    attribution = AttributionFactory()

    form = app.get(reverse('attribution-add', args=[dataset.pk])).forms['attribution-form']
    form['attribution'] = attribution.pk
    form['organization'].force_value(organization.pk)
    form['agent'] = "Test organization"
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        'Negalima užpildyti abiejų "Organizacija" ir "Agentas" laukų.'
    ]]


@pytest.mark.django_db
def test_dataset_create_attribution_without_organization_and_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()

    form = app.get(reverse('attribution-add', args=[dataset.pk])).forms['attribution-form']
    form['attribution'] = attribution.pk
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        'Privaloma užpildyti "Organizacija" arba "Agentas" lauką.'
    ]]


@pytest.mark.django_db
def test_dataset_create_attribution_with_existing_organization(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()
    organization = OrganizationFactory()
    DatasetAttributionFactory(
        dataset=dataset,
        attribution=attribution,
        organization=organization
    )

    form = app.get(reverse('attribution-add', args=[dataset.pk])).forms['attribution-form']
    form['attribution'] = attribution.pk
    form['organization'].force_value(organization.pk)
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        f'Ryšys "{attribution.title}" su šia organizacija jau egzistuoja.'
    ]]


@pytest.mark.django_db
def test_dataset_create_attribution_with_existing_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()
    DatasetAttributionFactory(
        dataset=dataset,
        attribution=attribution,
        agent="Test organization"
    )

    form = app.get(reverse('attribution-add', args=[dataset.pk])).forms['attribution-form']
    form['attribution'] = attribution.pk
    form['agent'] = "Test organization"
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        f'Ryšys "{attribution.title}" su šiuo agentu jau egzistuoja.'
    ]]


@pytest.mark.django_db
def test_dataset_create_attribution_with_organization(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    attribution = AttributionFactory()

    form = app.get(reverse('attribution-add', args=[dataset.pk])).forms['attribution-form']
    form['attribution'] = attribution.pk
    form['organization'].force_value(organization.pk)
    resp = form.submit()

    assert resp.url == dataset.get_absolute_url()
    assert dataset.datasetattribution_set.count() == 1
    assert dataset.datasetattribution_set.first().organization == organization
    assert dataset.datasetattribution_set.first().attribution == attribution
    assert dataset.datasetattribution_set.first().agent is None


@pytest.mark.django_db
def test_dataset_create_attribution_with_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()

    form = app.get(reverse('attribution-add', args=[dataset.pk])).forms['attribution-form']
    form['attribution'] = attribution.pk
    form['agent'] = "Test organization"
    resp = form.submit()

    assert resp.url == dataset.get_absolute_url()
    assert dataset.datasetattribution_set.count() == 1
    assert dataset.datasetattribution_set.first().agent == "Test organization"
    assert dataset.datasetattribution_set.first().attribution == attribution
    assert dataset.datasetattribution_set.first().organization is None


@pytest.mark.django_db
def test_dataset_delete_attribution(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_attribution = DatasetAttributionFactory()
    dataset = dataset_attribution.dataset

    resp = app.get(reverse('attribution-delete', args=[
        dataset.pk,
        dataset_attribution.pk
    ]))

    assert resp.url == dataset.get_absolute_url()
    assert dataset.datasetattribution_set.count() == 0


@pytest.mark.django_db
def test_dataset_with_type_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    series_type = TypeFactory(name='series')
    service_type = TypeFactory(name='service')

    form = app.get(reverse('dataset-change', args=[dataset.pk])).forms['dataset-form']
    form['type'] = [service_type.pk, series_type.pk]
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Tipai "service" ir "series" negali būti pažymėti abu kartu, gali būti pažymėtas tik vienas arba kitas.'
    ]]


@pytest.mark.django_db
def test_dataset_with_type(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    type = TypeFactory(name='service')
    service_type = DataServiceTypeFactory()
    service_spec_type = DataServiceSpecTypeFactory()

    form = app.get(reverse('dataset-change', args=[dataset.pk])).forms['dataset-form']
    form['type'] = [type.pk]
    form['endpoint_url'] = "https://test.com"
    form['endpoint_type'] = service_type.pk
    form['endpoint_description'] = "https://testdescription.com"
    form['endpoint_description_type'] = service_spec_type.pk
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.url == dataset.get_absolute_url()
    assert list(dataset.type.all()) == [type]
    assert dataset.series is False
    assert dataset.service is True
    assert dataset.endpoint_url == "https://test.com"
    assert dataset.endpoint_type == service_type
    assert dataset.endpoint_description == "https://testdescription.com"
    assert dataset.endpoint_description_type == service_spec_type


@pytest.mark.django_db
def test_dataset_add_relation_with_existing_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_relation = DatasetRelationFactory()

    form = app.get(reverse('dataset-relation-add', args=[dataset_relation.dataset.pk])).forms['dataset-relation-form']
    form['relation_type'] = f"{dataset_relation.relation.pk}"
    form['part_of'].force_value(dataset_relation.part_of.pk)
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        f'"{dataset_relation.relation.title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.'
    ]]


@pytest.mark.django_db
def test_dataset_add_relation_with_existing_inverse_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_relation = DatasetRelationFactory()

    form = app.get(reverse('dataset-relation-add', args=[dataset_relation.part_of.pk])).forms['dataset-relation-form']
    form['relation_type'] = f"{dataset_relation.relation.pk}_inv"
    form['part_of'].force_value(dataset_relation.dataset.pk)
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        f'"{dataset_relation.relation.inversive_title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.'
    ]]


@pytest.mark.django_db
def test_dataset_add_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    dataset_part_of = DatasetFactory()
    relation = RelationFactory()

    form = app.get(reverse('dataset-relation-add', args=[dataset.pk])).forms['dataset-relation-form']
    form['relation_type'] = f"{relation.pk}"
    form['part_of'].force_value(dataset_part_of.pk)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.url == dataset.get_absolute_url()
    assert dataset.part_of.count() == 1
    assert dataset.part_of.first().part_of == dataset_part_of
    assert dataset.part_of.first().relation == relation


@pytest.mark.django_db
def test_dataset_add_inverse_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    dataset_part_of = DatasetFactory()
    relation = RelationFactory()

    form = app.get(reverse('dataset-relation-add', args=[dataset.pk])).forms['dataset-relation-form']
    form['relation_type'] = f"{relation.pk}_inv"
    form['part_of'].force_value(dataset_part_of.pk)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.url == dataset.get_absolute_url()
    assert dataset_part_of.part_of.count() == 1
    assert dataset_part_of.part_of.first().part_of == dataset
    assert dataset_part_of.part_of.first().relation == relation


def _get_selected(context):
    selected = {
        f.name: [i.value for i in f.items() if i.selected]
        for f in context['filters']
    }
    selected = {
        k: (v[0] if len(v) == 1 else v)
        for k, v in selected.items() if v
    }
    return selected


@pytest.mark.django_db
def test_add_dataset_to_plan(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    plan = PlanFactory(
        deadline=(date.today() + timedelta(days=1))
    )

    form = app.get(reverse('dataset-plans-create', args=[dataset.pk])).forms['dataset-plan-form']
    form['plan'] = plan.pk
    resp = form.submit()

    assert resp.url == reverse('dataset-plans', args=[dataset.pk])
    assert dataset.plandataset_set.count() == 1
    assert dataset.plandataset_set.first().plan == plan


@pytest.mark.django_db
def test_dataset_create_non_public(app: DjangoTestApp):
    LicenceFactory(is_default=True)
    FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('dataset-add', kwargs={'pk': organization.id})).forms['dataset-form']
    form['title'] = 'Test dataset'
    form['is_public'] = False
    form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Test dataset")
    assert added_dataset.count() == 2
    assert added_dataset.first().is_public is False
    assert added_dataset.first().published is None


@pytest.mark.django_db
def test_dataset_create_public(app: DjangoTestApp):
    LicenceFactory(is_default=True)
    FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('dataset-add', kwargs={'pk': organization.id})).forms['dataset-form']
    form['title'] = 'Test dataset'
    form['is_public'] = True
    form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Test dataset")
    assert added_dataset.count() == 2
    assert added_dataset.first().is_public is True
    assert added_dataset.first().published is not None


@pytest.mark.django_db
def test_dataset_update_from_public_to_non_public(app: DjangoTestApp):
    LicenceFactory(is_default=True)
    FrequencyFactory(is_default=True)
    dataset = DatasetFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)

    assert dataset.is_public is True
    assert dataset.published is not None

    form = app.get(reverse('dataset-change', kwargs={'pk': dataset.id})).forms['dataset-form']
    form['is_public'] = False
    form.submit()
    dataset.refresh_from_db()

    assert dataset.is_public is False
    assert dataset.published is None


@pytest.mark.django_db
def test_dataset_update_from_non_public_to_public(app: DjangoTestApp):
    LicenceFactory(is_default=True)
    FrequencyFactory(is_default=True)
    dataset = DatasetFactory(
        is_public=False,
        published=None,
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)

    assert dataset.is_public is False
    assert dataset.published is None

    form = app.get(reverse('dataset-change', kwargs={'pk': dataset.id})).forms['dataset-form']
    form['is_public'] = True
    form.submit()
    dataset.refresh_from_db()

    assert dataset.is_public is True
    assert dataset.published is not None


@pytest.mark.django_db
def test_add_dataset_to_plan_title(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization)

    form = app.get(reverse('dataset-plans-create', args=[dataset.pk])).forms['plan-form']
    form.submit()

    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 1
    assert plan.first().title == "Duomenų atvėrimas"


@pytest.mark.django_db
def test_add_dataset_to_plan_title_with_distribution(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization)
    DatasetDistributionFactory(dataset=dataset)

    form = app.get(reverse('dataset-plans-create', args=[dataset.pk])).forms['plan-form']
    form.submit()

    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 1
    assert plan.first().title == "Duomenų rinkinio papildymas"


@pytest.mark.django_db
def test_delete_dataset_from_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.PLANNED)
    plan = PlanFactory()
    PlanDataset.objects.create(
        dataset=dataset,
        plan=plan
    )

    form = app.get(reverse('dataset-plans-delete', args=[plan.pk])).forms['delete-form']
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 0
    assert dataset.status == Dataset.INVENTORED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.INVENTORED


@pytest.mark.django_db
def test_delete_dataset_from_non_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.PLANNED)
    plan1 = PlanFactory()
    PlanDataset.objects.create(
        dataset=dataset,
        plan=plan1
    )
    plan2 = PlanFactory()
    PlanDataset.objects.create(
        dataset=dataset,
        plan=plan2
    )

    form = app.get(reverse('dataset-plans-delete', args=[plan2.pk])).forms['delete-form']
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 1
    assert dataset.status == Dataset.PLANNED
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_not_public_dataset_from_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(
        organization=organization,
        is_public=False,
        status=Dataset.UNASSIGNED
    )
    plan = PlanFactory()
    PlanDataset.objects.create(
        dataset=dataset,
        plan=plan
    )

    form = app.get(reverse('dataset-plans-delete', args=[plan.pk])).forms['delete-form']
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 0
    assert dataset.status == Dataset.UNASSIGNED
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_opened_dataset_from_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    DatasetDistributionFactory(dataset=dataset)
    plan = PlanFactory()
    PlanDataset.objects.create(
        dataset=dataset,
        plan=plan
    )

    form = app.get(reverse('dataset-plans-delete', args=[plan.pk])).forms['delete-form']
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 0
    assert dataset.status == Dataset.HAS_DATA
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_last_distribution_from_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource = DatasetDistributionFactory(dataset=dataset)

    app.get(reverse('resource-delete', args=[resource.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.INVENTORED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.INVENTORED


@pytest.mark.django_db
def test_delete_non_last_distribution_from_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource1 = DatasetDistributionFactory(dataset=dataset)
    resource2 = DatasetDistributionFactory(dataset=dataset)

    app.get(reverse('resource-delete', args=[resource2.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 1
    assert dataset.status == Dataset.HAS_DATA
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_last_distribution_from_non_public_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(
        organization=organization,
        status=Dataset.UNASSIGNED,
        is_public=False
    )
    resource = DatasetDistributionFactory(dataset=dataset)

    app.get(reverse('resource-delete', args=[resource.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.UNASSIGNED
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_last_distribution_from_dataset_with_plans(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource = DatasetDistributionFactory(dataset=dataset)
    plan = PlanFactory()
    PlanDataset.objects.create(
        dataset=dataset,
        plan=plan
    )

    app.get(reverse('resource-delete', args=[resource.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.PLANNED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.PLANNED


@pytest.mark.django_db
def test_dataset_with_name_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('dataset-change', args=[dataset.pk])).forms['dataset-form']
    form['name'] = "test/ąčę"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės.'
    ]]
