from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from factory.django import FileField

from vitrina.classifiers.factories import CategoryFactory, FrequencyFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory


@pytest.fixture
def datasets():
    dataset1 = DatasetFactory(
        slug="ds1",
        title="Duomenų rinkinys 1",
        title_en="Dataset 1",
        published=datetime(2022, 6, 1)
    )
    dataset2 = DatasetFactory(
        slug="ds2",
        title="Duomenų rinkinys 2 \"<'>\\",
        title_en="Dataset 2",
        published=datetime(2022, 8, 1)
    )
    dataset3 = DatasetFactory(
        slug="ds3",
        title="Duomenų rinkinys 3",
        title_en="Dataset 3",
        published=datetime(2022, 7, 1)
    )
    return [dataset1, dataset2, dataset3]


@pytest.mark.django_db
def test_search_without_query(app: DjangoTestApp, datasets):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "doesnt-match"))
    assert len(resp.context['object_list']) == 0


@pytest.mark.django_db
def test_search_with_query_that_matches_one(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "1"))
    assert list(resp.context['object_list']) == [datasets[0]]


@pytest.mark.django_db
def test_search_with_query_that_matches_all(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "rinkinys"))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_search_with_query_that_matches_all_with_english_title(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "dataset"))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_search_with_query_containing_special_characters(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "\"<'>\\"))
    assert list(resp.context['object_list']) == [datasets[1]]


@pytest.fixture
def status_filter_data():
    dataset1 = DatasetFactory(status=Dataset.HAS_DATA, slug="ds1")
    dataset2 = DatasetFactory(slug="ds2")
    DatasetStructureFactory(dataset=dataset2)
    return [dataset1, dataset2]


@pytest.mark.django_db
def test_status_filter_without_query(app: DjangoTestApp, status_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == status_filter_data
    assert resp.context['selected_status'] is None


@pytest.mark.django_db
def test_status_filter_has_data(app: DjangoTestApp, status_filter_data):
    resp = app.get("%s?status=%s" % (reverse('dataset-list'), Dataset.HAS_DATA))
    assert list(resp.context['object_list']) == [status_filter_data[0]]
    assert resp.context['selected_status'] == Dataset.HAS_DATA


@pytest.mark.django_db
def test_status_filter_has_structure(app: DjangoTestApp, status_filter_data):
    resp = app.get("%s?status=%s" % (reverse('dataset-list'), Dataset.HAS_STRUCTURE))
    assert list(resp.context['object_list']) == [status_filter_data[1]]
    assert resp.context['selected_status'] == Dataset.HAS_STRUCTURE


@pytest.fixture
def organization_filter_data():
    organization = OrganizationFactory()
    dataset_with_organization1 = DatasetFactory(organization=organization, slug="ds1")
    dataset_with_organization2 = DatasetFactory(organization=organization, slug="ds2")
    return {
        "organization": organization,
        "datasets": [dataset_with_organization1, dataset_with_organization2]
    }


@pytest.mark.django_db
def test_organization_filter_without_query(app: DjangoTestApp, organization_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == organization_filter_data["datasets"]
    assert resp.context['selected_organization'] is None


@pytest.mark.django_db
def test_organization_filter_with_organization(app: DjangoTestApp, organization_filter_data):
    resp = app.get("%s?organization=%s" % (reverse("dataset-list"),
                                           organization_filter_data["organization"].pk))
    assert list(resp.context['object_list']) == organization_filter_data["datasets"]
    assert resp.context['selected_organization'] == organization_filter_data["organization"].pk


@pytest.fixture
def category_filter_data():
    category1 = CategoryFactory()
    category2 = CategoryFactory(parent_id=category1.pk)
    category3 = CategoryFactory(parent_id=category1.pk)
    category4 = CategoryFactory(parent_id=category2.pk)
    dataset_with_category1 = DatasetFactory(category=category1, slug="ds1")
    dataset_with_category2 = DatasetFactory(category=category2, slug="ds2")
    dataset_with_category3 = DatasetFactory(category=category3, slug="ds3")
    dataset_with_category4 = DatasetFactory(category=category4, slug="ds4")
    return {
        "categories": [category1, category2, category3, category4],
        "datasets": [dataset_with_category1, dataset_with_category2, dataset_with_category3, dataset_with_category4]
    }


@pytest.mark.django_db
def test_category_filter_without_query(app: DjangoTestApp, category_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert len(resp.context['object_list']) == 4
    assert resp.context['selected_categories'] == []
    assert resp.context['related_categories'] == []


@pytest.mark.django_db
def test_category_filter_with_parent_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?category=%s" % (reverse("dataset-list"), category_filter_data["categories"][0].pk))
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
    resp = app.get("%s?category=%s" % (reverse("dataset-list"), category_filter_data["categories"][1].pk))
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
    resp = app.get("%s?category=%s" % (reverse("dataset-list"), category_filter_data["categories"][3].pk))
    assert list(resp.context['object_list']) == [category_filter_data["datasets"][3]]
    assert resp.context['selected_categories'] == [category_filter_data["categories"][3].pk]
    assert resp.context['related_categories'] == [
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][1].pk,
        category_filter_data["categories"][3].pk
    ]


@pytest.mark.django_db
def test_category_filter_with_parent_and_child_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?category=%s&category=%s" % (reverse("dataset-list"),
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
    dataset1 = DatasetFactory(tags="tag1, tag2, tag3", slug="ds1")
    dataset2 = DatasetFactory(tags="tag3, tag4, tag5, tag1", slug="ds2")
    return [dataset1, dataset2]


@pytest.mark.django_db
def test_tag_filter_without_query(app: DjangoTestApp, tag_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == tag_filter_data
    assert resp.context['selected_tags'] == []
    assert resp.context['related_tags'] == []


@pytest.mark.django_db
def test_tag_filter_with_one_tag(app: DjangoTestApp, tag_filter_data):
    resp = app.get("%s?tags=tag2" % reverse("dataset-list"))
    assert list(resp.context['object_list']) == [tag_filter_data[0]]
    assert resp.context['selected_tags'] == ['tag2']
    assert resp.context['related_tags'] == ['tag1', 'tag2', 'tag3']


@pytest.mark.django_db
def test_tag_filter_with_shared_tag(app: DjangoTestApp, tag_filter_data):
    resp = app.get("%s?tags=tag3" % reverse("dataset-list"))
    assert list(resp.context['object_list']) == tag_filter_data
    assert resp.context['selected_tags'] == ['tag3']
    assert resp.context['related_tags'] == ['tag1', 'tag2', 'tag3', 'tag4', 'tag5']


@pytest.mark.django_db
def test_tag_filter_with_multiple_tags(app: DjangoTestApp, tag_filter_data):
    resp = app.get("%s?tags=tag4&tags=tag3" % reverse("dataset-list"))
    assert list(resp.context['object_list']) == [tag_filter_data[1]]
    assert resp.context['selected_tags'] == ['tag4', 'tag3']
    assert resp.context['related_tags'] == ['tag1', 'tag3', 'tag4', 'tag5']


@pytest.fixture
def frequency_filter_data():
    frequency = FrequencyFactory()
    dataset1 = DatasetFactory(frequency=frequency, slug="ds1")
    dataset2 = DatasetFactory(frequency=frequency, slug="ds2")
    return {
        "frequency": frequency,
        "datasets": [dataset1, dataset2]
    }


@pytest.mark.django_db
def test_frequency_filter_without_query(app: DjangoTestApp, frequency_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == frequency_filter_data["datasets"]
    assert resp.context['selected_frequency'] is None


@pytest.mark.django_db
def test_frequency_filter_with_frequency(app: DjangoTestApp, frequency_filter_data):
    resp = app.get("%s?frequency=%s" % (reverse("dataset-list"),  frequency_filter_data["frequency"].pk))
    assert list(resp.context['object_list']) == frequency_filter_data["datasets"]
    assert resp.context['selected_frequency'] == frequency_filter_data["frequency"].pk


@pytest.fixture
def date_filter_data():
    dataset1 = DatasetFactory(published=datetime(2022, 3, 1), slug="ds1")
    dataset2 = DatasetFactory(published=datetime(2022, 2, 1), slug="ds2")
    dataset3 = DatasetFactory(published=datetime(2021, 12, 1), slug="ds3")
    return [dataset1, dataset2, dataset3]


@pytest.mark.django_db
def test_date_filter_without_query(app: DjangoTestApp, date_filter_data):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == date_filter_data
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] is None


@pytest.mark.django_db
def test_date_filter_wit_date_from(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-02-10" % reverse("dataset-list"))
    assert list(resp.context['object_list']) == [date_filter_data[0]]
    assert resp.context['selected_date_from'] == "2022-02-10"
    assert resp.context['selected_date_to'] is None


@pytest.mark.django_db
def test_date_filter_with_date_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_to=2022-02-10" % reverse("dataset-list"))
    assert list(resp.context['object_list']) == [date_filter_data[1], date_filter_data[2]]
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] == "2022-02-10"


@pytest.mark.django_db
def test_date_filter_with_dates_from_and_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-list"))
    assert list(resp.context['object_list']) == [date_filter_data[1]]
    assert resp.context['selected_date_from'] == "2022-01-01"
    assert resp.context['selected_date_to'] == "2022-02-10"


@pytest.mark.django_db
def test_dataset_filter_all(app: DjangoTestApp):
    organization = OrganizationFactory()
    category = CategoryFactory()
    frequency = FrequencyFactory()
    dataset_with_all_filters = DatasetFactory(
        status=Dataset.HAS_DATA,
        tags="tag1, tag2, tag3",
        published=datetime(2022, 2, 9),
        organization=organization,
        category=category,
        frequency=frequency
    )

    resp = app.get(reverse("dataset-list"), {
        'status': Dataset.HAS_DATA,
        'organization': organization.pk,
        'category': category.pk,
        'tags': ['tag1', 'tag2'],
        'frequency': frequency.pk,
        'date_from': '2022-01-01',
        'date_to': '2022-02-10',
    })

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


@pytest.fixture
def dataset_structure_data():
    organization = OrganizationFactory(slug="org", kind="gov")
    dataset1 = DatasetFactory(slug="ds2", organization=organization)
    dataset2 = DatasetFactory(slug="ds3", organization=organization)
    structure1 = DatasetStructureFactory(dataset=dataset1)
    structure2 = DatasetStructureFactory(dataset=dataset2, file=FileField(filename='file.csv', data=b'ab\0c'))
    return {
        'structure1': structure1,
        'structure2': structure2
    }


@pytest.mark.django_db
def test_with_structure(app: DjangoTestApp, dataset_structure_data):
    resp = app.get(dataset_structure_data['structure1'].get_absolute_url())
    assert resp.context['can_show'] is True
    assert list(resp.context['structure_data']) == [["Column"], ["Value"]]


@pytest.mark.django_db
def test_with_non_readable_structure(app: DjangoTestApp, dataset_structure_data):
    resp = app.get(dataset_structure_data['structure2'].get_absolute_url())
    assert resp.context['can_show'] is False
    assert resp.context['structure_data'] == []


@pytest.mark.django_db
def test_download_non_existent_structure(app: DjangoTestApp, dataset_structure_data):
    resp = app.get(reverse('dataset-structure-download', kwargs={
        'organization_kind': "doesntexist",
        'organization_slug': "doesntexist",
        'dataset_slug': "doesntexist"
    }), expect_errors=True)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_download_structure(app: DjangoTestApp, dataset_structure_data):
    resp = app.get(dataset_structure_data['structure1'].get_absolute_url() + "download")
    assert resp.content == b'Column\nValue'
