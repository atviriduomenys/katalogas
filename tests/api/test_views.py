import secrets
from datetime import datetime

import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.testing.templates import strip_empty_lines
from vitrina.api.exceptions import DuplicateAPIKeyException
from vitrina.api.factories import APIKeyFactory
from vitrina.api.models import ApiKey
from vitrina.catalogs.factories import CatalogFactory
from vitrina.classifiers.factories import CategoryFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory, OrganizationFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.statistics.models import ModelDownloadStats
from vitrina.users.factories import UserFactory
from vitrina.classifiers.factories import LicenceFactory
from vitrina.classifiers.factories import FrequencyFactory
from vitrina.resources.factories import FileFormat


@pytest.mark.django_db
def test_retrieve_catalog_list_without_api_key(app: DjangoTestApp):
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_catalog_list_with_disabled_api_key(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(
        representative=representative,
        enabled=False
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_catalog_list_with_expired_api_key(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(
        representative=representative,
        expires=timezone.make_aware(datetime(2000, 12, 24))
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_catalog_list_with_duplicate_api_key(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    key = secrets.token_urlsafe()
    APIKeyFactory(
        api_key=f"{ApiKey.DUPLICATE}-0-{key}",
        representative=representative,
        enabled=False
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {key}'
    })
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403
    assert res.json['detail'] == DuplicateAPIKeyException.default_detail.format(
        url=f"http://{domain}{reverse('organization-members', args=[organization.pk])}"
    )


@pytest.mark.django_db
def test_retrieve_catalog_list_with_correct_api_key(app: DjangoTestApp):
    catalog = CatalogFactory()
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.json == [{
        'description': catalog.description,
        'id': str(catalog.identifier),
        'licence': {
            'description': catalog.licence.description,
            'id': str(catalog.licence.identifier),
            'title': catalog.licence.title
        },
        'title': catalog.title
    }]


@pytest.mark.django_db
def test_retrieve_category_list_without_api_key(app: DjangoTestApp):
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_category_list_with_disabled_api_key(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(
        representative=representative,
        enabled=False
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_category_list_with_expired_api_key(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(
        representative=representative,
        expires=timezone.make_aware(datetime(2000, 12, 24))
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_category_list_with_duplicate_api_key(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    key = secrets.token_urlsafe()
    APIKeyFactory(
        api_key=f"{ApiKey.DUPLICATE}-0-{key}",
        representative=representative,
        enabled=False
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {key}'
    })
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403
    assert res.json['detail'] == DuplicateAPIKeyException.default_detail.format(
        url=f"http://{domain}{reverse('organization-members', args=[organization.pk])}"
    )


@pytest.mark.django_db
def test_retrieve_category_list_with_correct_api_key(app: DjangoTestApp):
    category = CategoryFactory()
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.json == [{
        'description': category.description,
        'id': str(category.pk),
        'title': category.title
    }]


@pytest.mark.django_db
def test_retrieve_licence_list_without_api_key(app: DjangoTestApp):
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_licence_licence_list_with_disabled_api_key(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(
        representative=representative,
        enabled=False
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_licence_licence_list_with_expired_api_key(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(
        representative=representative,
        expires=timezone.make_aware(datetime(2000, 12, 24))
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_licence_list_with_duplicate_api_key(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    key = secrets.token_urlsafe()
    APIKeyFactory(
        api_key=f"{ApiKey.DUPLICATE}-0-{key}",
        representative=representative,
        enabled=False
    )
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {key}'
    })
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403
    assert res.json['detail'] == DuplicateAPIKeyException.default_detail.format(
        url=f"http://{domain}{reverse('organization-members', args=[organization.pk])}"
    )


@pytest.mark.django_db
def test_retrieve_licence_list_with_correct_api_key(app: DjangoTestApp):
    licence = LicenceFactory()
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.json == [{
        'description': licence.description,
        'id': str(licence.identifier),
        'title': licence.title
    }]


@pytest.mark.django_db
def test_get_all_datasets_without_api_key(app: DjangoTestApp):
    res = app.get(reverse("api-dataset"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_get_all_datasets(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory(is_public=False)
    category = CategoryFactory()
    dataset.category.add(category)
    DatasetFactory()
    DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-dataset"))
    dataset.refresh_from_db()
    assert res.json == [{
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
        'organization_id': dataset.organization.id,
        'organization_title': dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "spatial": dataset.spatial_coverage,
        "licence": dataset.licence.identifier,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title]
    }]


@pytest.mark.django_db
def test_get_dataset_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.get(reverse("api-single-dataset", kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_get_dataset_from_different_organization(app: DjangoTestApp):
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-single-dataset", kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_get_dataset_with_dataset_id(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-single-dataset", kwargs={
        'datasetId': dataset.pk
    }))
    dataset.refresh_from_db()
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
        'organization_id': dataset.organization.id,
        'organization_title': dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "spatial": dataset.spatial_coverage,
        "licence": dataset.licence.identifier,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title]
    }


@pytest.mark.django_db
def test_get_dataset_with_wrong_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-single-dataset-internal", kwargs={
        'internalId': "wrong"
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_get_dataset_with_internal_id(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory(internal_id="test")
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse("api-single-dataset-internal", kwargs={
        'internalId': dataset.internal_id
    }))
    dataset.refresh_from_db()
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
        'organization_id': dataset.organization.id,
        'organization_title': dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "spatial": dataset.spatial_coverage,
        "licence": dataset.licence.identifier,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title]
    }


@pytest.mark.django_db
def test_create_dataset_without_api_key(app: DjangoTestApp):
    res = app.post(reverse("api-dataset"), {
        'title': "New dataset"
    }, expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_with_errors(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.post(reverse("api-dataset"), expect_errors=True)
    assert res.status_code == 400
    assert 'title' in res.json
    assert 'description' in res.json


@pytest.mark.django_db
def test_create_dataset(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    organization = OrganizationFactory()
    licence = LicenceFactory()
    frequency = FrequencyFactory()
    category = CategoryFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.post(reverse("api-dataset"), {
        'title': 'Test dataset',
        'description': 'Test dataset',
        'language': [
            'en',
            'lt'
        ],
        'keyword': [
            'tag1',
            'tag2'
        ],
        'licence': licence.identifier,
        'periodicity': frequency.title,
        'theme': [category.title]
    })
    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.language == "en lt"
    assert list(dataset.tags.all()) == ['tag1', 'tag2']
    assert dataset.licence == licence
    assert dataset.frequency == frequency
    assert list(dataset.category.all()) == [category]
    assert dataset.organization == organization
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.CREATED
    assert Version.objects.get_for_object(dataset).first().revision.user == representative.user
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": Dataset.API_ORIGIN,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
        'organization_id': dataset.organization.id,
        'organization_title': dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": ['en', 'lt'],
        "spatial": dataset.spatial_coverage,
        "licence": dataset.licence.identifier,
        "periodicity": dataset.frequency.title,
        "keyword": ['tag1', 'tag2'],
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title]
    }


@pytest.mark.django_db
def test_update_dataset_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.patch(reverse("api-single-dataset", kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_update_dataset_from_different_organization(app: DjangoTestApp):
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.patch(reverse("api-single-dataset", kwargs={'datasetId': dataset.pk}), {
        'title': "Updated title",
        'description': "Updated description"
    }, expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_update_dataset_with_dataset_id(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.patch(reverse("api-single-dataset", kwargs={'datasetId': dataset.pk}), {
        'title': "Updated title",
        'description': "Updated description"
    })
    dataset.refresh_from_db()
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.EDITED
    assert Version.objects.get_for_object(dataset).first().revision.user == representative.user
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": "Updated title",
        "description": "Updated description",
        "modified": timezone.localtime(dataset.modified).isoformat(),
        'organization_id': dataset.organization.id,
        'organization_title': dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "spatial": dataset.spatial_coverage,
        "licence": dataset.licence.identifier,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title]
    }


@pytest.mark.django_db
def test_update_dataset_with_internal_id(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory(internal_id="test")
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.patch(reverse("api-single-dataset-internal", kwargs={'internalId': dataset.internal_id}), {
        'title': "Updated title",
        'description': "Updated description"
    })
    dataset.refresh_from_db()
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.EDITED
    assert Version.objects.get_for_object(dataset).first().revision.user == representative.user
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": "Updated title",
        "description": "Updated description",
        "modified": timezone.localtime(dataset.modified).isoformat(),
        'organization_id': dataset.organization.id,
        'organization_title': dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "spatial": dataset.spatial_coverage,
        "licence": dataset.licence.identifier,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title]
    }


@pytest.mark.django_db
def test_delete_dataset_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.delete(reverse('api-single-dataset', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_delete_dataset_from_different_organization(app: DjangoTestApp):
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.delete(reverse('api-single-dataset', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_delete_dataset_with_dataset_id(app: DjangoTestApp):
    dataset = DatasetFactory(
        internal_id="test",
        slug="test"
    )
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    app.delete(reverse('api-single-dataset', kwargs={
        'datasetId': dataset.pk
    }))
    dataset.refresh_from_db()
    assert dataset.internal_id is None
    assert dataset.slug is None
    assert dataset.deleted is True
    assert dataset.deleted_on is not None
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.DELETED
    assert Version.objects.get_for_object(dataset).first().revision.user == representative.user


@pytest.mark.django_db
def test_delete_dataset_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(
        internal_id="test",
        slug="test"
    )
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    app.delete(reverse('api-single-dataset-internal', kwargs={
        'internalId': dataset.internal_id
    }))
    dataset.refresh_from_db()
    assert dataset.internal_id is None
    assert dataset.slug is None
    assert dataset.deleted is True
    assert dataset.deleted_on is not None
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.DELETED
    assert Version.objects.get_for_object(dataset).first().revision.user == representative.user


@pytest.mark.django_db
def test_get_all_dataset_distributions_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.get(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_get_all_dataset_distributions_with_dataset_id(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    distribution = DatasetDistributionFactory()
    DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse('api-distribution', kwargs={
        'datasetId': distribution.dataset.pk
    }))
    assert res.json == [{
        'description': distribution.description,
        'file': distribution.filename_without_path(),
        'geo_location': distribution.geo_location,
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': str(distribution.period_end),
        'periodStart': str(distribution.period_start),
        'title': distribution.title,
        'type': distribution.type,
        'url': f"http://{domain}{distribution.dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }]


@pytest.mark.django_db
def test_get_all_dataset_distributions_with_internal_id(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory(internal_id="test")
    distribution = DatasetDistributionFactory(dataset=dataset)
    DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse('api-distribution-internal', kwargs={
        'internalId': dataset.internal_id
    }))
    assert res.json == [{
        'description': distribution.description,
        'file': distribution.filename_without_path(),
        'geo_location': distribution.geo_location,
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': str(distribution.period_end),
        'periodStart': str(distribution.period_start),
        'title': distribution.title,
        'type': distribution.type,
        'url': f"http://{domain}{dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }]


@pytest.mark.django_db
def test_get_all_distributions(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(dataset=dataset, upload_to_storage=True)
    DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse('api-all-distributions-upload-to-storage'))
    assert res.json == [{
        'dataset_id': distribution.dataset.id,
        'description': distribution.description,
        'file': distribution.filename_without_path(),
        'geo_location': distribution.geo_location,
        'id': distribution.pk,
        'issued': distribution.issued,
        'organization_id': distribution.dataset.organization.id,
        'periodEnd': str(distribution.period_end),
        'periodStart': str(distribution.period_start),
        'title': distribution.title,
        'type': distribution.type,
        'update_interval': distribution.dataset.frequency.hours,
        'url': f"http://{domain}{dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }]


@pytest.mark.django_db
def test_create_dataset_distribution_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_distribution_without_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution")
    ], files=[])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json
    assert 'url' in res.json


@pytest.mark.django_db
def test_create_dataset_distribution_with_both_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('url', "https://test.com/")
    ], files=[('file', 'file.csv', b'Test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json
    assert 'url' in res.json


@pytest.mark.django_db
def test_create_dataset_distribution_with_empty_file(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('url', "https://test.com/")
    ], files=[('file', 'file.csv', b'')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json


@pytest.mark.django_db
def test_create_dataset_distribution_with_not_allowed_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12")
    ], files=[('file', 'file.exe', b'Test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json


@pytest.mark.django_db
def test_create_dataset_distribution_with_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12")
    ], files=[('file', 'file.csv', b'Test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    assert res.json == {
        'description': distribution.description,
        'file': distribution.filename_without_path(),
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': None,
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Test distribution",
        'type': "FILE",
        'url': f"http://{domain}{dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_create_dataset_distribution_with_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12"),
        ('url', "http://test.com/")
    ], files=[])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    assert res.json == {
        'description': distribution.description,
        'file': "",
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': None,
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Test distribution",
        'type': "URL",
        'url': "http://test.com/",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_create_dataset_distribution_with_overwrite(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12"),
        ('overwrite', True)
    ], files=[('file', distribution.filename_without_path(), b'Test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution', kwargs={
        'datasetId': distribution.dataset.pk
    }), params)
    assert distribution.dataset.datasetdistribution_set.count() == 1
    distribution = distribution.dataset.datasetdistribution_set.first()
    assert res.json == {
        'description': distribution.description,
        'file': distribution.filename_without_path(),
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': str(distribution.period_end),
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Test distribution",
        'type': "FILE",
        'url': f"http://{domain}{distribution.dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_create_dataset_distribution_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12"),
        ('url', "http://test.com/")
    ], files=[])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-distribution-internal', kwargs={
        'internalId': dataset.internal_id
    }), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    assert res.json == {
        'description': distribution.description,
        'file': "",
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': None,
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Test distribution",
        'type': "URL",
        'url': "http://test.com/",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_put_create_dataset_distribution_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.put(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_put_create_dataset_distribution_without_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution")
    ], files=[])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.put(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json
    assert 'url' in res.json


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_both_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('url', "https://test.com/")
    ], files=[('file', 'file.csv', b'Test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.put(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json
    assert 'url' in res.json


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_empty_file(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('url', "https://test.com/")
    ], files=[('file', 'file.csv', b'')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.put(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12")
    ], files=[('file', 'file.csv', b'Test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.put(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    assert res.json == {
        'description': distribution.description,
        'file': distribution.filename_without_path(),
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': None,
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Test distribution",
        'type': "FILE",
        'url': f"http://{domain}{dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12"),
        ('url', "http://test.com/")
    ], files=[])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.put(reverse('api-distribution', kwargs={
        'datasetId': dataset.pk
    }), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    assert res.json == {
        'description': distribution.description,
        'file': "",
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': None,
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Test distribution",
        'type': "URL",
        'url': "http://test.com/",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('periodStart', "2022-10-12"),
        ('url', "http://test.com/")
    ], files=[])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.put(reverse('api-distribution-internal', kwargs={
        'internalId': dataset.internal_id
    }), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    assert res.json == {
        'description': distribution.description,
        'file': "",
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': None,
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Test distribution",
        'type': "URL",
        'url': "http://test.com/",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_update_dataset_distribution_without_api_key(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_update_dataset_distribution_with_wrong_dataset_id(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    another_dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': another_dataset.pk,
        'distributionId': distribution.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_update_dataset_distribution_with_wrong_internal_id(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    another_dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.patch(reverse('api-single-distribution-internal', kwargs={
        'internalId': another_dataset.internal_id,
        'distributionId': distribution.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_update_dataset_distribution_with_both_file_and_url(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
        ('url', 'http://example.com/')
    ], files=[('file', 'file.csv', b'Test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json
    assert 'url' in res.json


@pytest.mark.django_db
def test_update_dataset_distribution_with_empty_file(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test distribution"),
    ], files=[('file', 'file.csv', b'')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
    assert 'file' in res.json


@pytest.mark.django_db
def test_update_dataset_distribution_with_not_allowed_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Updated title"),
        ('description', "Updated description"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
    ], files=[('file', 'updated_file.html', b'test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), params, expect_errors=True)
    assert 'file' in res.json


@pytest.mark.django_db
def test_update_dataset_distribution_with_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Updated title"),
        ('description', "Updated description"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
    ], files=[('file', 'updated_file.csv', b'test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), params)
    distribution.refresh_from_db()
    assert res.json == {
        'description': "Updated description",
        'file': distribution.filename_without_path(),
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': str(distribution.period_end),
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Updated title",
        'type': "FILE",
        'url': f"http://{domain}{distribution.dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_update_dataset_distribution_with_url(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Updated title"),
        ('description', "Updated description"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
        ('url', "http://example.com/")
    ], files=[])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), params)
    assert res.json == {
        'description': "Updated description",
        'file': "",
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': str(distribution.period_end),
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Updated title",
        'type': "URL",
        'url': "http://example.com/",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_update_dataset_distribution_with_internal_id(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory(internal_id="test")
    distribution = DatasetDistributionFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Updated title"),
        ('description', "Updated description"),
        ('region', 'Geo'),
        ('municipality', 'Location'),
    ], files=[('file', 'updated_file.csv', b'test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.patch(reverse('api-single-distribution-internal', kwargs={
        'internalId': dataset.internal_id,
        'distributionId': distribution.pk
    }), params)
    distribution.refresh_from_db()
    assert res.json == {
        'description': "Updated description",
        'file': distribution.filename_without_path(),
        'id': distribution.pk,
        'issued': distribution.issued,
        'periodEnd': str(distribution.period_end),
        'periodStart': str(distribution.period_start),
        'geo_location': "Geo Location",
        'title': "Updated title",
        'type': "FILE",
        'url': f"http://{domain}{dataset.get_absolute_url()}",
        'version': distribution.distribution_version,
        'upload_to_storage': distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_delete_dataset_distribution_without_api_key(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    res = app.delete(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_delete_dataset_distribution_with_wrong_dataset_id(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    another_dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.delete(reverse('api-single-distribution', kwargs={
        'datasetId': another_dataset.pk,
        'distributionId': distribution.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_delete_dataset_distribution_with_wrong_internal_id(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    another_dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.delete(reverse('api-single-distribution-internal', kwargs={
        'internalId': another_dataset.internal_id,
        'distributionId': distribution.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_delete_dataset_distribution_with_dataset_id(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    app.delete(reverse('api-single-distribution', kwargs={
        'datasetId': dataset.pk,
        'distributionId': distribution.pk
    }))
    assert dataset.datasetdistribution_set.count() == 0


@pytest.mark.django_db
def test_delete_dataset_distribution_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    distribution = DatasetDistributionFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    app.delete(reverse('api-single-distribution-internal', kwargs={
        'internalId': dataset.internal_id,
        'distributionId': distribution.pk
    }))
    assert dataset.datasetdistribution_set.count() == 0


@pytest.mark.django_db
def test_get_dataset_structures_without_api_key(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    res = app.get(reverse('api-structure', kwargs={
        'datasetId': structure.dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_get_dataset_structures_with_dataset_id(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    DatasetStructureFactory()
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse('api-structure', kwargs={
        'datasetId': structure.dataset.pk
    }))
    assert res.json == [{
        'created': timezone.localtime(structure.created).isoformat(),
        'filename': structure.filename_without_path(),
        'id': structure.pk,
        'size': structure.size,
        'title': structure.title
    }]


@pytest.mark.django_db
def test_get_dataset_structures_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    structure = DatasetStructureFactory(dataset=dataset)
    DatasetStructureFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.get(reverse('api-structure-internal', kwargs={
        'internalId': dataset.internal_id
    }))
    assert res.json == [{
        'created': timezone.localtime(structure.created).isoformat(),
        'filename': structure.filename_without_path(),
        'id': structure.pk,
        'size': structure.size,
        'title': structure.title
    }]


@pytest.mark.django_db
def test_create_dataset_structures_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.post(reverse('api-structure', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_structure_with_errors(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.post(reverse('api-structure', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert dataset.datasetstructure_set.count() == 0
    assert 'file' in res.json
    assert 'title' in res.json


@pytest.mark.django_db
def test_create_dataset_structure_with_not_allowed_file(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test structure")
    ], files=[('file', 'file.svg', b'test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-structure', kwargs={
        'datasetId': dataset.pk
    }), params, expect_errors=True)
    assert 'file' in res.json


@pytest.mark.django_db
def test_create_dataset_structure_with_dataset_id(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test structure")
    ], files=[('file', 'file.csv', b'test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-structure', kwargs={
        'datasetId': dataset.pk
    }), params)
    dataset.refresh_from_db()
    assert dataset.datasetstructure_set.count() == 1
    structure = dataset.datasetstructure_set.first()
    assert dataset.current_structure == structure
    assert res.json == {
        'created': timezone.localtime(structure.created).isoformat(),
        'filename': structure.filename_without_path(),
        'id': structure.pk,
        'size': structure.size,
        'title': structure.title
    }


@pytest.mark.django_db
def test_create_dataset_structure_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[
        ('title', "Test structure")
    ], files=[('file', 'file.csv', b'test')])
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test',
        'CONTENT_TYPE': content_type
    })
    res = app.post(reverse('api-structure-internal', kwargs={
        'internalId': dataset.internal_id
    }), params)
    dataset.refresh_from_db()
    assert dataset.datasetstructure_set.count() == 1
    structure = dataset.datasetstructure_set.first()
    assert dataset.current_structure == structure
    assert res.json == {
        'created': timezone.localtime(structure.created).isoformat(),
        'filename': structure.filename_without_path(),
        'id': structure.pk,
        'size': structure.size,
        'title': structure.title
    }


@pytest.mark.django_db
def test_delete_dataset_structures_without_api_key(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    res = app.delete(reverse('api-single-structure', kwargs={
        'datasetId': structure.dataset.pk,
        'structureId': structure.pk
    }), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_delete_dataset_structure_with_wrong_dataset_id(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    another_dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.delete(reverse('api-single-structure', kwargs={
        'datasetId': another_dataset.pk,
        'structureId': structure.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_delete_dataset_structure_with_wrong_internal_id(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    another_dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.delete(reverse('api-single-structure-internal', kwargs={
        'internalId': another_dataset.internal_id,
        'structureId': structure.pk
    }), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_delete_dataset_structure_with_dataset_id(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    dataset = structure.dataset
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    app.delete(reverse('api-single-structure', kwargs={
        'datasetId': dataset.pk,
        'structureId': structure.pk
    }))
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.django_db
def test_delete_dataset_structure_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    structure = DatasetStructureFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    app.delete(reverse('api-single-structure-internal', kwargs={
        'internalId': dataset.internal_id,
        'structureId': structure.pk
    }))
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.django_db
def test_create_model_statistics(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    user = UserFactory(
        is_staff=True
    )
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        user=user
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': 'ApiKey test'
    })
    res = app.post(reverse('api-download-stats-internal'), {
        'source': 'get.data.gov.lt',
        'model': 'naujas_modelis',
        'format': 'excel',
        'time': datetime.now(),
        'requests': 100,
        'objects': 10
    }, expect_errors=False)
    assert res.json == {
        "source": "get.data.gov.lt",
        "model": "naujas_modelis",
        "format": "excel",
        "time": timezone.localtime(ModelDownloadStats.objects.first().created).isoformat(),
        "requests": 100,
        "objects": 10
    }


@pytest.mark.django_db
def test_edp_dcat_ap_rdf(app: DjangoTestApp):
    iana = 'http://www.iana.org/assignments'
    po = 'http://publications.europa.eu/resource/authority'

    dataset = DatasetFactory(
        title={
            'lt': 'Testas1',
            'en': 'Test1',
        },
        description={
            'lt': 'Duomenų rinkinio aprašymas.',
            'en': 'Dataset description.',
        },
        published=datetime(2016, 8, 1),
        licence=LicenceFactory(url=f'{po}/licence/CC_BY_4_0'),
        frequency=FrequencyFactory(uri=f'{po}/frequency/IRREG'),
        category=[
            CategoryFactory(title='Energy'),
            CategoryFactory(
                title='Environment',
                uri=f'{po}/data-theme/ENVI',
            ),
        ],
        organization=OrganizationFactory(
            title='Data Enterprise',
            email='data@example.com',
        ),
    )
    dist1 = DatasetDistributionFactory(
        dataset=dataset,
        title="CSV failas",
        description="Atviras duomenų šaltinis.",
        format=FileFormat(
            uri=f'{po}/file-type/CSV',
            media_type_uri=f'{iana}/media-types/text/csv',
        ),
    )
    dist2 = DatasetDistributionFactory(
        dataset=dataset,
        title="Duomenų teikimo paslauga",
        description="Universali duomenų teikimo paslauga.",
        format=FileFormat(
            extension='UAPI',
            uri=f'{po}/file-type/JSON',
            media_type_uri=f'{iana}/media-types/application/json',
        ),
    )

    res = app.get('/edp/dcat-ap.rdf')

    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/rdf+xml'
    assert strip_empty_lines(res.text) == f'''\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://example.com"
    xmlns:edp="https://europeandataportal.eu/voc#"
    xmlns:dct="http://purl.org/dc/terms/"
    xmlns:spdx="http://spdx.org/rdf/terms#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:j.0="http://data.europa.eu/88u/ontology/dcatapop#"
    xmlns:adms="http://www.w3.org/ns/adms#"
    xmlns:dqv="http://www.w3.org/ns/dqv#"
    xmlns:vcard="http://www.w3.org/2006/vcard/ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#"
    xmlns:schema="http://schema.org/"
    xmlns:dcat="http://www.w3.org/ns/dcat#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:dcatap="http://data.europa.eu/r5r/"
    xmlns:eli="https://data.europa.eu/eli/">
    <dcat:Dataset rdf:about="http://example.com/datasets/{dataset.id}/">
        <dct:title xml:lang="en">Test1</dct:title>
        <dct:description xml:lang="en">Dataset description.</dct:description>
        <dct:title xml:lang="lt">Testas1</dct:title>
        <dct:description xml:lang="lt">Duomenų rinkinio aprašymas.</dct:description>
        <dcat:theme>
            <skos:Concept>
                <skos:prefLabel xml:lang="lt">Energy</skos:prefLabel>
            </skos:Concept>
        </dcat:theme>
        <dcat:theme>
            <skos:Concept rdf:about="http://publications.europa.eu/resource/authority/data-theme/ENVI"/>
        </dcat:theme>
        <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2016-08-01</dct:issued>
        <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dataset.modified.strftime("%Y-%m-%d")}</dct:modified>
        <dct:accessRights rdf:resource="http://publications.europa.eu/resource/authority/access-right/PUBLIC"/>
        <dct:publisher>
            <foaf:Organization>
                <foaf:name>Data Enterprise</foaf:name>
                <foaf:mbox rdf:resource="mailto:data@example.com"/>
            </foaf:Organization>
        </dct:publisher>
        <dct:accrualPeriodicity>
            <dct:Frequency rdf:about="http://publications.europa.eu/resource/authority/frequency/IRREG"/>
        </dct:accrualPeriodicity>
        <dcat:contactPoint>
            <vcard:Kind>
                <vcard:hasEmail rdf:resource="mailto:data@example.com"/>
            </vcard:Kind>
        </dcat:contactPoint>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist1.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">CSV failas</dct:title>
                <dct:description xml:lang="lt">Atviras duomenų šaltinis.</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="http://example.com/datasets/{dataset.id}/"/>
                <dcat:downloadURL rdf:resource="{dist1.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement rdf:about="http://publications.europa.eu/resource/authority/access-right/PUBLIC"/>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/text/csv"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/CSV"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist2.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/WEB_SERVICE"/>
                <dct:title xml:lang="lt">Duomenų teikimo paslauga</dct:title>
                <dct:description xml:lang="lt">Universali duomenų teikimo paslauga.</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="http://example.com/datasets/{dataset.id}/"/>
                <dcat:downloadURL rdf:resource="{dist2.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement rdf:about="http://publications.europa.eu/resource/authority/access-right/PUBLIC"/>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/application/json"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/JSON"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
    </dcat:Dataset>
</rdf:RDF>'''
