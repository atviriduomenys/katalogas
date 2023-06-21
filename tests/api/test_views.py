import secrets
from datetime import datetime

import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.api.exceptions import DuplicateAPIKeyException
from vitrina.api.factories import APIKeyFactory
from vitrina.api.models import ApiKey
from vitrina.catalogs.factories import CatalogFactory
from vitrina.classifiers.factories import LicenceFactory, FrequencyFactory, CategoryFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory, OrganizationFactory
from vitrina.resources.factories import DatasetDistributionFactory


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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
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
    dataset_from_another_org1 = DatasetFactory()
    dataset_from_another_org2 = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    api_key = APIKeyFactory(representative=representative)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
    })
    res = app.get(reverse("api-dataset"))
    assert res.json == [{
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
    })
    res = app.get(reverse("api-single-dataset", kwargs={
        'datasetId': dataset.pk
    }))
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
    })
    res = app.get(reverse("api-single-dataset-internal", kwargs={
        'internalId': dataset.internal_id
    }))
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
        'CONTENT_TYPE': content_type
    })
    res = app.patch(reverse('api-single-distribution', kwargs={
        'datasetId': distribution.dataset.pk,
        'distributionId': distribution.pk
    }), params, expect_errors=True)
    assert res.status_code == 400
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'version': distribution.distribution_version
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
    })
    res = app.post(reverse('api-structure', kwargs={
        'datasetId': dataset.pk
    }), expect_errors=True)
    assert dataset.datasetstructure_set.count() == 0
    assert 'file' in res.json
    assert 'title' in res.json


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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}",
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
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
        'HTTP_AUTHORIZATION': f"ApiKey {api_key.api_key}"
    })
    app.delete(reverse('api-single-structure-internal', kwargs={
        'internalId': dataset.internal_id,
        'structureId': structure.pk
    }))
    assert dataset.datasetstructure_set.count() == 0
