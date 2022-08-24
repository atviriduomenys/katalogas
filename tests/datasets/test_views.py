from datetime import datetime

import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import CategoryFactory, FrequencyFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory


@pytest.fixture
def status_filter_data():
    dataset1 = DatasetFactory(status=Dataset.HAS_DATA)
    dataset2 = DatasetFactory()
    DatasetStructureFactory(dataset=dataset2)
    return [dataset1, dataset2]


@pytest.mark.django_db
def test_status_filter_without_query(app: DjangoTestApp, status_filter_data):
    resp = app.get(reverse('dataset-search-results'))
    assert list(resp.context['object_list']) == status_filter_data
    assert resp.context['selected_status'] is None


@pytest.mark.django_db
def test_status_filter_has_data(app: DjangoTestApp, status_filter_data):
    resp = app.get("%s?status=%s" % (reverse('dataset-search-results'), Dataset.HAS_DATA))
    assert list(resp.context['object_list']) == [status_filter_data[0]]
    assert resp.context['selected_status'] == Dataset.HAS_DATA


@pytest.mark.django_db
def test_status_filter_has_structure(app: DjangoTestApp, status_filter_data):
    resp = app.get("%s?status=%s" % (reverse('dataset-search-results'), Dataset.HAS_STRUCTURE))
    assert list(resp.context['object_list']) == [status_filter_data[1]]
    assert resp.context['selected_status'] == Dataset.HAS_STRUCTURE


@pytest.fixture
def organization_filter_data():
    organization = OrganizationFactory()
    dataset_with_organization1 = DatasetFactory(organization=organization)
    dataset_with_organization2 = DatasetFactory(organization=organization)
    return {
        "organization": organization,
        "datasets": [dataset_with_organization1, dataset_with_organization2]
    }


@pytest.mark.django_db
def test_organization_filter_without_query(app: DjangoTestApp, organization_filter_data):
    resp = app.get(reverse('dataset-search-results'))
    assert list(resp.context['object_list']) == organization_filter_data["datasets"]
    assert resp.context['selected_organization'] is None


@pytest.mark.django_db
def test_organization_filter_with_organization(app: DjangoTestApp, organization_filter_data):
    resp = app.get("%s?organization=%s" % (reverse("dataset-search-results"),
                                           organization_filter_data["organization"].pk))
    assert list(resp.context['object_list']) == organization_filter_data["datasets"]
    assert resp.context['selected_organization'] == organization_filter_data["organization"].pk


@pytest.fixture
def category_filter_data():
    category1 = CategoryFactory()
    category2 = CategoryFactory(parent_id=category1.pk)
    category3 = CategoryFactory(parent_id=category1.pk)
    category4 = CategoryFactory(parent_id=category2.pk)
    dataset_with_category1 = DatasetFactory(category=category1)
    dataset_with_category2 = DatasetFactory(category=category2)
    dataset_with_category3 = DatasetFactory(category=category3)
    dataset_with_category4 = DatasetFactory(category=category4)
    return {
        "categories": [category1, category2, category3, category4],
        "datasets": [dataset_with_category1, dataset_with_category2, dataset_with_category3, dataset_with_category4]
    }


@pytest.mark.django_db
def test_category_filter_without_query(app: DjangoTestApp, category_filter_data):
    resp = app.get(reverse('dataset-search-results'))
    assert len(resp.context['object_list']) == 4
    assert resp.context['selected_categories'] == []
    assert resp.context['related_categories'] == []


@pytest.mark.django_db
def test_category_filter_with_parent_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?category=%s" % (reverse("dataset-search-results"), category_filter_data["categories"][0].pk))
    assert list(resp.context['object_list']) == category_filter_data["datasets"]
    assert resp.context['selected_categories'] == [category_filter_data["categories"][0].pk]
    assert resp.context['related_categories'] == [
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][1].pk,
        category_filter_data["categories"][2].pk,
        category_filter_data["categories"][3].pk
    ]


@pytest.mark.django_db
def test_category_filter_with_middle_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?category=%s" % (reverse("dataset-search-results"), category_filter_data["categories"][1].pk))
    assert list(resp.context['object_list']) == [
        category_filter_data["datasets"][1],
        category_filter_data["datasets"][3],
    ]
    assert resp.context['selected_categories'] == [category_filter_data["categories"][1].pk]
    assert resp.context['related_categories'] == [
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][1].pk,
        category_filter_data["categories"][3].pk
    ]


@pytest.mark.django_db
def test_category_filter_with_child_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?category=%s" % (reverse("dataset-search-results"), category_filter_data["categories"][3].pk))
    assert list(resp.context['object_list']) == [category_filter_data["datasets"][3]]
    assert resp.context['selected_categories'] == [category_filter_data["categories"][3].pk]
    assert resp.context['related_categories'] == [
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][1].pk,
        category_filter_data["categories"][3].pk
    ]


@pytest.mark.django_db
def test_category_filter_with_parent_and_child_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?category=%s&category=%s" % (reverse("dataset-search-results"),
                                                   category_filter_data["categories"][0].pk,
                                                   category_filter_data["categories"][3].pk))
    assert list(resp.context['object_list']) == [category_filter_data["datasets"][3]]
    assert resp.context['selected_categories'] == [
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][3].pk
    ]
    assert resp.context['related_categories'] == [
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][1].pk,
        category_filter_data["categories"][3].pk
    ]


@pytest.fixture
def tag_filter_data():
    dataset1 = DatasetFactory(tags="tag1, tag2, tag3")
    dataset2 = DatasetFactory(tags="tag3, tag4, tag5, tag1")
    return [dataset1, dataset2]


@pytest.mark.django_db
def test_tag_filter_without_query(app: DjangoTestApp, tag_filter_data):
    resp = app.get(reverse('dataset-search-results'))
    assert list(resp.context['object_list']) == tag_filter_data
    assert resp.context['selected_tags'] == []
    assert resp.context['related_tags'] == []


@pytest.mark.django_db
def test_tag_filter_with_one_tag(app: DjangoTestApp, tag_filter_data):
    resp = app.get("%s?tags=tag2" % reverse("dataset-search-results"))
    assert list(resp.context['object_list']) == [tag_filter_data[0]]
    assert resp.context['selected_tags'] == ['tag2']
    assert resp.context['related_tags'] == ['tag1', 'tag2', 'tag3']


@pytest.mark.django_db
def test_tag_filter_with_shared_tag(app: DjangoTestApp, tag_filter_data):
    resp = app.get("%s?tags=tag3" % reverse("dataset-search-results"))
    assert list(resp.context['object_list']) == tag_filter_data
    assert resp.context['selected_tags'] == ['tag3']
    assert resp.context['related_tags'] == ['tag1', 'tag2', 'tag3', 'tag4', 'tag5']


@pytest.mark.django_db
def test_tag_filter_with_multiple_tags(app: DjangoTestApp, tag_filter_data):
    resp = app.get("%s?tags=tag4&tags=tag3" % reverse("dataset-search-results"))
    assert list(resp.context['object_list']) == [tag_filter_data[1]]
    assert resp.context['selected_tags'] == ['tag4', 'tag3']
    assert resp.context['related_tags'] == ['tag1', 'tag3', 'tag4', 'tag5']


@pytest.fixture
def frequency_filter_data():
    frequency = FrequencyFactory()
    dataset1 = DatasetFactory(frequency=frequency)
    dataset2 = DatasetFactory(frequency=frequency)
    return {
        "frequency": frequency,
        "datasets": [dataset1, dataset2]
    }


@pytest.mark.django_db
def test_frequency_filter_without_query(app: DjangoTestApp, frequency_filter_data):
    resp = app.get(reverse('dataset-search-results'))
    assert list(resp.context['object_list']) == frequency_filter_data["datasets"]
    assert resp.context['selected_frequency'] is None


@pytest.mark.django_db
def test_frequency_filter_with_frequency(app: DjangoTestApp, frequency_filter_data):
    resp = app.get("%s?frequency=%s" % (reverse("dataset-search-results"),  frequency_filter_data["frequency"].pk))
    assert list(resp.context['object_list']) == frequency_filter_data["datasets"]
    assert resp.context['selected_frequency'] == frequency_filter_data["frequency"].pk


@pytest.fixture
def date_filter_data():
    dataset1 = DatasetFactory(published=datetime(2022, 3, 1))
    dataset2 = DatasetFactory(published=datetime(2022, 2, 1))
    dataset3 = DatasetFactory(published=datetime(2021, 12, 1))
    return [dataset1, dataset2, dataset3]


@pytest.mark.django_db
def test_date_filter_without_query(app: DjangoTestApp, date_filter_data):
    resp = app.get(reverse('dataset-search-results'))
    assert list(resp.context['object_list']) == date_filter_data
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] is None


@pytest.mark.django_db
def test_date_filter_wit_date_from(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-02-10" % reverse("dataset-search-results"))
    assert list(resp.context['object_list']) == [date_filter_data[0]]
    assert resp.context['selected_date_from'] == "2022-02-10"
    assert resp.context['selected_date_to'] is None


@pytest.mark.django_db
def test_date_filter_with_date_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_to=2022-02-10" % reverse("dataset-search-results"))
    assert list(resp.context['object_list']) == [date_filter_data[1], date_filter_data[2]]
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] == "2022-02-10"


@pytest.mark.django_db
def test_date_filter_with_dates_from_and_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-search-results"))
    assert list(resp.context['object_list']) == [date_filter_data[1]]
    assert resp.context['selected_date_from'] == "2022-01-01"
    assert resp.context['selected_date_to'] == "2022-02-10"


@pytest.mark.django_db
def test_dataset_filter_all(app: DjangoTestApp):
    organization = OrganizationFactory()
    category = CategoryFactory()
    frequency = FrequencyFactory()
    dataset_with_all_filters = DatasetFactory(status=Dataset.HAS_DATA, tags="tag1, tag2, tag3", published=datetime(2022, 2, 9),
                                              organization=organization, category=category, frequency=frequency)

    resp = app.get("%s?status=%s&organization=%s&category=%s&tags=tag1&tags=tag2&frequency=%s&"
                   "date_from=2022-01-01&date_to=2022-02-10" % (reverse("dataset-search-results"), Dataset.HAS_DATA,
                                                                organization.pk, category.pk, frequency.pk))

    assert list(resp.context['object_list']) == [dataset_with_all_filters]
    assert resp.context['selected_status'] == Dataset.HAS_DATA
    assert resp.context['selected_organization'] == organization.pk
    assert resp.context['selected_categories'] == [category.pk]
    assert resp.context['related_categories'] == [category.pk]
    assert resp.context['selected_tags'] == ["tag1", "tag2"]
    assert resp.context['related_tags'] == ["tag1", "tag2", "tag3"]
    assert resp.context['selected_frequency'] == frequency.pk
    assert resp.context['selected_date_from'] == "2022-01-01"
    assert resp.context['selected_date_to'] == "2022-02-10"


