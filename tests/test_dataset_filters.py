from datetime import datetime

import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import CategoryFactory, FrequencyFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.views import HAS_DATA, INVENTORED, METADATA, HAS_STRUCTURE
from vitrina.orgs.factories import OrganizationFactory


@pytest.mark.django_db
def test_dataset_filter_status(app: DjangoTestApp):
    dataset_has_data = DatasetFactory(status=HAS_DATA)
    dataset_inventored = DatasetFactory(status=INVENTORED)
    dataset_metadata = DatasetFactory(status=METADATA)
    dataset_structure = DatasetStructureFactory()
    dataset_structure.dataset = dataset_has_data
    dataset_structure.save()

    # without query
    resp = app.get(reverse('dataset-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 3
    assert resp.context['selected_status'] is None

    # with status HAS_DATA
    resp = app.get("%s?status=%s" % (reverse('dataset-search-results'), HAS_DATA))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_has_data.pk
    assert resp.context['selected_status'] == HAS_DATA

    # with status INVENTORED
    resp = app.get("%s?status=%s" % (reverse('dataset-search-results'), INVENTORED))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_inventored.pk
    assert resp.context['selected_status'] == INVENTORED

    # with status METADATA
    resp = app.get("%s?status=%s" % (reverse('dataset-search-results'), METADATA))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_metadata.pk
    assert resp.context['selected_status'] == METADATA

    # with status HAS_STRUCTURE
    resp = app.get("%s?status=%s" % (reverse('dataset-search-results'), HAS_STRUCTURE))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_has_data.pk
    assert resp.context['selected_status'] == HAS_STRUCTURE


@pytest.mark.django_db
def test_dataset_filter_organization(app: DjangoTestApp):
    organization = OrganizationFactory()
    dataset_with_organization1 = DatasetFactory()
    dataset_with_organization2 = DatasetFactory()
    dataset_with_organization1.organization = organization
    dataset_with_organization1.save()
    dataset_with_organization2.organization = organization
    dataset_with_organization2.save()

    # without query
    resp = app.get(reverse('dataset-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['selected_organization'] is None

    # with organization
    resp = app.get("%s?organization=%s" % (reverse("dataset-search-results"), organization.pk))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['selected_organization'] == organization.pk


@pytest.mark.django_db
def test_dataset_filter_category(app: DjangoTestApp):
    category1 = CategoryFactory()
    category2 = CategoryFactory(parent_id=category1.pk)
    category3 = CategoryFactory(parent_id=category1.pk)
    category4 = CategoryFactory(parent_id=category2.pk)
    dataset_with_category1 = DatasetFactory(category=category1)
    dataset_with_category2 = DatasetFactory(category=category2)
    dataset_with_category3 = DatasetFactory(category=category3)
    dataset_with_category4 = DatasetFactory(category=category4)

    # without query
    resp = app.get(reverse('dataset-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 4
    assert resp.context['selected_categories'] == []
    assert resp.context['related_categories'] == []

    # with parent category
    resp = app.get("%s?category=%s" % (reverse("dataset-search-results"), category1.pk))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 4
    assert resp.context['selected_categories'] == [category1.pk]
    assert category1.pk in resp.context['related_categories']
    assert category2.pk in resp.context['related_categories']
    assert category3.pk in resp.context['related_categories']
    assert category4.pk in resp.context['related_categories']

    # with middle category
    resp = app.get("%s?category=%s" % (reverse("dataset-search-results"), category2.pk))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['object_list'][0].pk == dataset_with_category2.pk
    assert resp.context['object_list'][1].pk == dataset_with_category4.pk
    assert resp.context['selected_categories'] == [category2.pk]
    assert category1.pk in resp.context['related_categories']
    assert category2.pk in resp.context['related_categories']
    assert category4.pk in resp.context['related_categories']

    # with child category
    resp = app.get("%s?category=%s" % (reverse("dataset-search-results"), category4.pk))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_with_category4.pk
    assert resp.context['selected_categories'] == [category4.pk]
    assert category1.pk in resp.context['related_categories']
    assert category2.pk in resp.context['related_categories']
    assert category4.pk in resp.context['related_categories']

    # with parent and child categories
    resp = app.get("%s?category=%s&category=%s" % (reverse("dataset-search-results"), category1.pk, category4.pk))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_with_category4.pk
    assert resp.context['selected_categories'] == [category1.pk, category4.pk]
    assert category1.pk in resp.context['related_categories']
    assert category2.pk in resp.context['related_categories']
    assert category4.pk in resp.context['related_categories']


@pytest.mark.django_db
def test_dataset_filter_tags(app: DjangoTestApp):
    dataset_with_tags1 = DatasetFactory(tags="tag1, tag2, tag3")
    dataset_with_tags2 = DatasetFactory(tags="tag3, tag4, tag5, tag1")

    # without query
    resp = app.get(reverse('dataset-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['selected_tags'] == []
    assert resp.context['related_tags'] == []

    # with one dataset tag
    resp = app.get("%s?tags=tag2" % reverse("dataset-search-results"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_with_tags1.pk
    assert resp.context['selected_tags'] == ['tag2']
    assert 'tag1' in resp.context['related_tags']
    assert 'tag3' in resp.context['related_tags']

    # with shared tag
    resp = app.get("%s?tags=tag3" % reverse("dataset-search-results"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['selected_tags'] == ['tag3']
    assert 'tag1' in resp.context['related_tags']
    assert 'tag2' in resp.context['related_tags']
    assert 'tag4' in resp.context['related_tags']
    assert 'tag5' in resp.context['related_tags']

    # with multiple tags
    resp = app.get("%s?tags=tag4&tags=tag3" % reverse("dataset-search-results"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_with_tags2.pk
    assert 'tag1' in resp.context['related_tags']
    assert 'tag5' in resp.context['related_tags']


@pytest.mark.django_db
def test_dataset_filter_frequency(app: DjangoTestApp):
    frequency = FrequencyFactory()
    dataset_with_frequency1 = DatasetFactory()
    dataset_with_frequency2 = DatasetFactory()
    dataset_with_frequency1.frequency = frequency
    dataset_with_frequency1.save()
    dataset_with_frequency2.frequency = frequency
    dataset_with_frequency2.save()

    # without query
    resp = app.get(reverse('dataset-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['selected_frequency'] is None

    # with frequency
    resp = app.get("%s?frequency=%s" % (reverse("dataset-search-results"), frequency.pk))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['selected_frequency'] == frequency.pk


@pytest.mark.django_db
def test_dataset_filter_date(app: DjangoTestApp):
    dataset_with_published1 = DatasetFactory(published=datetime(2022, 3, 1))
    dataset_with_published2 = DatasetFactory(published=datetime(2022, 2, 1))
    dataset_with_published3 = DatasetFactory(published=datetime(2021, 12, 1))

    # without query
    resp = app.get(reverse('dataset-search-results'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 3
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] is None

    # with date from
    resp = app.get("%s?date_from=2022-02-10" % reverse("dataset-search-results"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_with_published1.pk
    assert resp.context['selected_date_from'] == "2022-02-10"
    assert resp.context['selected_date_to'] is None

    # with date to
    resp = app.get("%s?date_to=2022-02-10" % reverse("dataset-search-results"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['object_list'][0].pk == dataset_with_published2.pk
    assert resp.context['object_list'][1].pk == dataset_with_published3.pk
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] == "2022-02-10"

    # with date from and date to
    resp = app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-search-results"))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_with_published2.pk
    assert resp.context['selected_date_from'] == "2022-01-01"
    assert resp.context['selected_date_to'] == "2022-02-10"


@pytest.mark.django_db
def test_dataset_filter_all(app: DjangoTestApp):
    dataset_with_all_filters = DatasetFactory(status=HAS_DATA, tags="tag1, tag2, tag3", published=datetime(2022, 2, 9))
    organization = OrganizationFactory()
    category = CategoryFactory()
    frequency = FrequencyFactory()
    dataset_with_all_filters.organization = organization
    dataset_with_all_filters.category = category
    dataset_with_all_filters.frequency = frequency
    dataset_with_all_filters.save()

    resp = app.get("%s?status=%s&organization=%s&category=%s&tags=tag1&tags=tag2&frequency=%s&"
                   "date_from=2022-01-01&date_to=2022-02-10" % (reverse("dataset-search-results"), HAS_DATA,
                                                                organization.pk, category.pk, frequency.pk))

    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == dataset_with_all_filters.pk
    assert resp.context['selected_status'] == HAS_DATA
    assert resp.context['selected_organization'] == organization.pk
    assert resp.context['selected_categories'] == [category.pk]
    assert resp.context['related_categories'] == [category.pk]
    assert resp.context['selected_tags'] == ["tag1", "tag2"]
    assert 'tag1' in resp.context['related_tags']
    assert 'tag2' in resp.context['related_tags']
    assert 'tag3' in resp.context['related_tags']
    assert resp.context['selected_frequency'] == frequency.pk
    assert resp.context['selected_date_from'] == "2022-01-01"
    assert resp.context['selected_date_to'] == "2022-02-10"


