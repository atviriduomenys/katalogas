import secrets
from datetime import datetime

import pytest
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.structure import VersionStatus
from vitrina.testing.templates import strip_empty_lines
from vitrina.api.exceptions import DuplicateAPIKeyException
from vitrina.api.factories import APIKeyFactory
from vitrina.api.models import ApiKey
from vitrina.catalogs.factories import CatalogFactory
from vitrina.classifiers.factories import CategoryFactory
from vitrina.datasets.factories import (
    DatasetFactory,
    DatasetStructureFactory,
    DatasetGroupFactory,
    DCATResourceSubclassFactory,
    DatasetGroupCategoryUriFactory,
)
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory, OrganizationFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.statistics.models import ModelDownloadStats
from vitrina.users.factories import UserFactory
from vitrina.classifiers.factories import LicenceFactory
from vitrina.classifiers.factories import FrequencyFactory
from vitrina.resources.factories import FileFormat
from vitrina.utils import RevisionComment, RevisionSource

from vitrina.api.helpers import _encode_xml_control_chars


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
    APIKeyFactory(representative=representative, enabled=False)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
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
    APIKeyFactory(representative=representative, expires=timezone.make_aware(datetime(2000, 12, 24)))
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
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
    APIKeyFactory(api_key=f"{ApiKey.DUPLICATE}-0-{key}", representative=representative, enabled=False)
    app.extra_environ.update({"HTTP_AUTHORIZATION": f"ApiKey {key}"})
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403
    assert res.json["detail"] == DuplicateAPIKeyException.default_detail.format(
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.json == [
        {
            "description": catalog.description,
            "id": str(catalog.identifier),
            "licence": {
                "description": catalog.licence.description,
                "id": str(catalog.licence.identifier),
                "title": catalog.licence.title,
            },
            "title": catalog.title,
        }
    ]


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
    APIKeyFactory(representative=representative, enabled=False)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
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
    APIKeyFactory(representative=representative, expires=timezone.make_aware(datetime(2000, 12, 24)))
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
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
    APIKeyFactory(api_key=f"{ApiKey.DUPLICATE}-0-{key}", representative=representative, enabled=False)
    app.extra_environ.update({"HTTP_AUTHORIZATION": f"ApiKey {key}"})
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403
    assert res.json["detail"] == DuplicateAPIKeyException.default_detail.format(
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.json == [{"description": category.description, "id": str(category.pk), "title": category.title}]


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
    APIKeyFactory(representative=representative, enabled=False)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
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
    APIKeyFactory(representative=representative, expires=timezone.make_aware(datetime(2000, 12, 24)))
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
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
    APIKeyFactory(api_key=f"{ApiKey.DUPLICATE}-0-{key}", representative=representative, enabled=False)
    app.extra_environ.update({"HTTP_AUTHORIZATION": f"ApiKey {key}"})
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403
    assert res.json["detail"] == DuplicateAPIKeyException.default_detail.format(
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    data = [licence_obj for licence_obj in res.json if licence_obj["id"] == str(licence.identifier)]
    assert data == [{"description": licence.description, "id": str(licence.identifier), "title": licence.title}]


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
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-dataset"))
    dataset.refresh_from_db()
    assert res.json == [
        {
            "created": timezone.localtime(dataset.created).isoformat(),
            "id": str(dataset.pk),
            "internalId": dataset.internal_id,
            "origin": dataset.origin,
            "title": dataset.title,
            "description": dataset.description,
            "modified": timezone.localtime(dataset.modified).isoformat(),
            "organization_id": dataset.organization.id,
            "organization_title": dataset.organization.title,
            "temporalCoverage": dataset.temporal_coverage,
            "language": dataset.language_array,
            "publisher": None,
            "spatial": dataset.spatial_coverage,
            "periodicity": dataset.frequency.title,
            "keyword": dataset.tag_name_array,
            "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
            "theme": [category.title],
        }
    ]


@pytest.mark.parametrize(
    "access_rights,expected",
    [
        (Dataset.NON_PUBLIC, []),
        (Dataset.CONFIDENTIAL, []),
    ],
)
@pytest.mark.django_db
def test_get_all_non_public_datasets_open_data_representative(app: DjangoTestApp, access_rights: str, expected: list):
    dataset = DatasetFactory(access_rights=access_rights)
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
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-dataset"))
    dataset.refresh_from_db()
    assert res.json == expected


@pytest.mark.parametrize(
    "access_rights,expected",
    [
        (Dataset.NON_PUBLIC, []),
        (Dataset.CONFIDENTIAL, []),
    ],
)
@pytest.mark.django_db
def test_get_all_non_public_datasets_open_data_representative_organization(
    app: DjangoTestApp, access_rights: str, expected: list
):
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    DatasetFactory(is_public=False, organization=org, access_rights=access_rights)
    DatasetFactory()
    ct = ContentType.objects.get_for_model(org)
    representative = RepresentativeFactory(content_type=ct, object_id=org.pk, user=None, organization=publisher_org)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-dataset"), expect_errors=True)
    assert res.json == []


@pytest.mark.django_db
def test_get_dataset_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.get(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}), expect_errors=True)
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}), expect_errors=True)
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}))
    dataset.refresh_from_db()
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
        "organization_id": dataset.organization.id,
        "organization_title": dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "publisher": None,
        "spatial": dataset.spatial_coverage,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title],
    }


@pytest.mark.parametrize(
    "access_rights",
    [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL],
)
@pytest.mark.django_db
def test_get_non_public_dataset_with_dataset_id_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}), expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 404


@pytest.mark.parametrize(
    "access_rights",
    [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL],
)
@pytest.mark.django_db
def test_get_non_public_dataset_with_dataset_id_open_data_representative_organization(
    app: DjangoTestApp, access_rights: str
):
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    dataset = DatasetFactory(is_public=False, organization=org, access_rights=access_rights)
    DatasetFactory()
    ct = ContentType.objects.get_for_model(org)
    representative = RepresentativeFactory(content_type=ct, object_id=org.pk, user=None, organization=publisher_org)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_get_dataset_with_wrong_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-single-dataset-internal", kwargs={"internalId": "wrong"}), expect_errors=True)
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-single-dataset-internal", kwargs={"internalId": dataset.internal_id}))
    dataset.refresh_from_db()
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
        "organization_id": dataset.organization.id,
        "organization_title": dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "publisher": None,
        "spatial": dataset.spatial_coverage,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title],
    }


@pytest.mark.parametrize(
    "access_rights",
    [
        Dataset.NON_PUBLIC,
        Dataset.CONFIDENTIAL,
    ],
)
@pytest.mark.django_db
def test_get_non_public_dataset_with_internal_id_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(
        reverse("api-single-dataset-internal", kwargs={"internalId": dataset.internal_id}), expect_errors=True
    )
    dataset.refresh_from_db()
    assert res.status_code == 404


@pytest.mark.parametrize(
    "access_rights",
    [
        Dataset.NON_PUBLIC,
        Dataset.CONFIDENTIAL,
    ],
)
@pytest.mark.django_db
def test_get_non_public_dataset_with_dataset_internal_id_open_data_representative_organization(
    app: DjangoTestApp, access_rights
):
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    dataset = DatasetFactory(internal_id="test", is_public=False, organization=org, access_rights=access_rights)
    DatasetFactory()
    ct = ContentType.objects.get_for_model(org)
    representative = RepresentativeFactory(content_type=ct, object_id=org.pk, user=None, organization=publisher_org)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(
        reverse("api-single-dataset-internal", kwargs={"internalId": dataset.internal_id}), expect_errors=True
    )
    dataset.refresh_from_db()
    assert res.status_code == 404


@pytest.mark.django_db
def test_create_dataset_without_api_key(app: DjangoTestApp):
    res = app.post(reverse("api-dataset"), {"title": "New dataset"}, expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_with_errors(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.post(reverse("api-dataset"), expect_errors=True)
    assert res.status_code == 400
    assert "title" in res.json
    assert "description" in res.json


@pytest.mark.django_db
def test_create_dataset(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    organization = OrganizationFactory()
    frequency = FrequencyFactory()
    category = CategoryFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-dataset")
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW, action="api-dataset", http_method="POST", path=url, args=[], kwargs={}
    )
    res = app.post(
        url,
        {
            "title": "Test dataset",
            "description": "Test dataset",
            "language": ["en", "lt"],
            "keyword": ["tag1", "tag2"],
            "periodicity": frequency.title,
            "theme": [category.title],
        },
    )
    dataset_objects = Dataset.objects.exclude(id=1)

    assert dataset_objects.count() == 1
    dataset = dataset_objects.first()
    assert dataset.language == "en lt"
    assert list(dataset.tags.all()) == ["tag1", "tag2"]
    assert dataset.frequency == frequency
    assert list(dataset.category.all()) == [category]
    assert dataset.organization == organization
    assert Version.objects.get_for_object(dataset).count() == 1
    assert dataset.metadata.first().metadata_version.status == VersionStatus.DRAFT
    assert dataset.metadata.first().title == "Test dataset"
    assert dataset.metadata.first().description == "Test dataset"
    assert dataset.metadata.first().version == 1
    assert dataset.metadata.first().object_id == dataset.pk
    version = Version.objects.get_for_object(dataset).select_related("revision").first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == representative.user
    assert dataset.metadata.count() == 1
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": Dataset.API_ORIGIN,
        "title": dataset.title,
        "description": dataset.description,
        "modified": timezone.localtime(dataset.modified).isoformat(),
        "organization_id": dataset.organization.id,
        "organization_title": dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": ["en", "lt"],
        "publisher": None,
        "spatial": dataset.spatial_coverage,
        "periodicity": dataset.frequency.title,
        "keyword": ["tag1", "tag2"],
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title],
    }


@pytest.mark.django_db
def test_update_dataset_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.patch(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}), expect_errors=True)
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.patch(
        reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}),
        {"title": "Updated title", "description": "Updated description"},
        expect_errors=True,
    )
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset", kwargs={"datasetId": dataset.pk})
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="api-single-dataset",
        http_method="PATCH",
        path=url,
        args=[],
        kwargs={"datasetId": dataset.pk},
    )
    res = app.patch(url, {"title": "Updated title", "description": "Updated description"})
    dataset.refresh_from_db()
    assert Version.objects.get_for_object(dataset).count() == 1
    version = Version.objects.get_for_object(dataset).first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == representative.user
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": "Updated title",
        "description": "Updated description",
        "modified": timezone.localtime(dataset.modified).isoformat(),
        "organization_id": dataset.organization.id,
        "organization_title": dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "publisher": None,
        "spatial": dataset.spatial_coverage,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title],
    }


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_update_non_public_dataset_with_dataset_id_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(access_rights=access_rights)
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset", kwargs={"datasetId": dataset.pk})
    res = app.patch(url, {"title": "Updated title", "description": "Updated description"}, expect_errors=True)
    dataset.refresh_from_db()
    assert dataset.title != "Updated title"
    assert dataset.description != "Updated description"
    assert res.status_code == 404


@pytest.mark.django_db
def test_update_information_system_with_dataset_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(subclass=DCATResourceSubclassFactory(name="information_system"))
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset", kwargs={"datasetId": dataset.pk})
    res = app.patch(url, {"title": "Updated title", "description": "Updated description"}, expect_errors=True)
    dataset.refresh_from_db()
    assert dataset.title != "Updated title"
    assert dataset.description != "Updated description"
    assert res.status_code == 403


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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset-internal", kwargs={"internalId": dataset.internal_id})
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="api-single-dataset-internal",
        http_method="PATCH",
        path=url,
        args=[],
        kwargs={"internalId": dataset.internal_id},
    )
    res = app.patch(url, {"title": "Updated title", "description": "Updated description"})
    dataset.refresh_from_db()
    assert Version.objects.get_for_object(dataset).count() == 1
    version = Version.objects.get_for_object(dataset).select_related("revision").first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == representative.user
    assert res.json == {
        "created": timezone.localtime(dataset.created).isoformat(),
        "id": str(dataset.pk),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": "Updated title",
        "description": "Updated description",
        "modified": timezone.localtime(dataset.modified).isoformat(),
        "organization_id": dataset.organization.id,
        "organization_title": dataset.organization.title,
        "temporalCoverage": dataset.temporal_coverage,
        "language": dataset.language_array,
        "publisher": None,
        "spatial": dataset.spatial_coverage,
        "periodicity": dataset.frequency.title,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{dataset.get_absolute_url()}",
        "theme": [category.title],
    }


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_update_non_public_dataset_with_internal_id_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset-internal", kwargs={"internalId": dataset.internal_id})
    res = app.patch(url, {"title": "Updated title", "description": "Updated description"}, expect_errors=True)
    dataset.refresh_from_db()
    assert dataset.title != "Updated title"
    assert dataset.description != "Updated description"
    assert res.status_code == 404


@pytest.mark.django_db
def test_update_information_system_with_internal_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test", subclass=DCATResourceSubclassFactory(name="information_system"))
    category = CategoryFactory()
    dataset.category.add(category)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset-internal", kwargs={"internalId": dataset.internal_id})
    res = app.patch(url, {"title": "Updated title", "description": "Updated description"}, expect_errors=True)
    dataset.refresh_from_db()
    assert dataset.title != "Updated title"
    assert dataset.description != "Updated description"
    assert res.status_code == 403


@pytest.mark.django_db
def test_delete_dataset_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.delete(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}), expect_errors=True)
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(reverse("api-single-dataset", kwargs={"datasetId": dataset.pk}), expect_errors=True)
    assert res.status_code == 404


@pytest.mark.django_db
def test_delete_dataset_with_dataset_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test", slug="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset", kwargs={"datasetId": dataset.pk})
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="api-single-dataset",
        http_method="DELETE",
        path=url,
        args=[],
        kwargs={"datasetId": dataset.pk},
    )
    app.delete(url)
    dataset.refresh_from_db()
    assert dataset.internal_id is None
    assert dataset.slug is None
    assert dataset.deleted is True
    assert dataset.deleted_on is not None
    assert Version.objects.get_for_object(dataset).count() == 1
    version = Version.objects.get_for_object(dataset).select_related("revision").first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == representative.user


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_delete_non_public_dataset_with_dataset_id_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(internal_id="test", slug="test", access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset", kwargs={"datasetId": dataset.pk})
    res = app.delete(url, expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 404
    assert dataset.internal_id == "test"
    assert dataset.slug == "test"
    assert dataset.deleted is None
    assert dataset.deleted_on is None


@pytest.mark.django_db
def test_delete_information_system_with_dataset_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(
        internal_id="test", slug="test", subclass=DCATResourceSubclassFactory(name="information_system")
    )
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    url = reverse("api-single-dataset", kwargs={"datasetId": dataset.pk})
    res = app.delete(url, expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 403
    assert dataset.internal_id == "test"
    assert dataset.slug == "test"
    assert dataset.deleted is None
    assert dataset.deleted_on is None


@pytest.mark.django_db
def test_delete_dataset_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test", slug="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    kwargs_dict = {"internalId": dataset.internal_id}
    url = reverse("api-single-dataset-internal", kwargs=kwargs_dict)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="api-single-dataset-internal",
        http_method="DELETE",
        path=url,
        args=[],
        kwargs=kwargs_dict,
    )
    app.delete(url)
    dataset.refresh_from_db()
    assert dataset.internal_id is None
    assert dataset.slug is None
    assert dataset.deleted is True
    assert dataset.deleted_on is not None
    assert Version.objects.get_for_object(dataset).count() == 1
    version = Version.objects.get_for_object(dataset).select_related("revision").first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == representative.user


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_delete_non_public_dataset_with_internal_id_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(internal_id="test", slug="test", access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    kwargs_dict = {"internalId": dataset.internal_id}
    url = reverse("api-single-dataset-internal", kwargs=kwargs_dict)
    res = app.delete(url, expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 404
    assert dataset.internal_id == "test"
    assert dataset.slug == "test"
    assert dataset.deleted is None
    assert dataset.deleted_on is None


@pytest.mark.django_db
def test_delete_information_system_with_internal_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(
        internal_id="test", slug="test", subclass=DCATResourceSubclassFactory(name="information_system")
    )
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    kwargs_dict = {"internalId": dataset.internal_id}
    url = reverse("api-single-dataset-internal", kwargs=kwargs_dict)
    res = app.delete(url, expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 403
    assert dataset.internal_id == "test"
    assert dataset.slug == "test"
    assert dataset.deleted is None
    assert dataset.deleted_on is None


@pytest.mark.django_db
def test_get_all_dataset_distributions_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.get(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), expect_errors=True)
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-distribution", kwargs={"datasetId": distribution.dataset.pk}))
    assert res.json == [
        {
            "description": distribution.description,
            "file": distribution.filename_without_path(),
            "geo_location": distribution.geo_location,
            "id": distribution.pk,
            "issued": distribution.issued,
            "periodEnd": str(distribution.period_end),
            "periodStart": str(distribution.period_start),
            "title": distribution.title,
            "type": distribution.type,
            "url": f"http://{domain}{distribution.dataset.get_absolute_url()}",
            "version": distribution.distribution_version,
            "upload_to_storage": distribution.upload_to_storage,
        }
    ]


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_get_all_non_public_dataset_distributions_with_dataset_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    distribution.dataset.access_rights = access_rights
    distribution.dataset.save(update_fields=["access_rights"])
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-distribution", kwargs={"datasetId": distribution.dataset.pk}), expect_errors=True)
    assert res.status_code == 403


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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}))
    assert res.json == [
        {
            "description": distribution.description,
            "file": distribution.filename_without_path(),
            "geo_location": distribution.geo_location,
            "id": distribution.pk,
            "issued": distribution.issued,
            "periodEnd": str(distribution.period_end),
            "periodStart": str(distribution.period_start),
            "title": distribution.title,
            "type": distribution.type,
            "url": f"http://{domain}{dataset.get_absolute_url()}",
            "version": distribution.distribution_version,
            "upload_to_storage": distribution.upload_to_storage,
        }
    ]


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_get_all_non_public_dataset_distributions_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    DatasetDistributionFactory(dataset=dataset)
    DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}), expect_errors=True)
    assert res.status_code == 403


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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-all-distributions-upload-to-storage"))
    assert res.json == [
        {
            "dataset_id": distribution.dataset.id,
            "description": distribution.description,
            "file": distribution.filename_without_path(),
            "geo_location": distribution.geo_location,
            "id": distribution.pk,
            "issued": distribution.issued,
            "organization_id": distribution.dataset.organization.id,
            "periodEnd": str(distribution.period_end),
            "periodStart": str(distribution.period_start),
            "title": distribution.title,
            "type": distribution.type,
            "update_interval": distribution.dataset.frequency.hours,
            "url": f"http://{domain}{dataset.get_absolute_url()}",
            "version": distribution.distribution_version,
            "upload_to_storage": distribution.upload_to_storage,
        }
    ]


@pytest.mark.django_db
def test_create_dataset_distribution_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_distribution_without_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[("title", "Test distribution")], files=[])
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 400
    assert "file" in res.json
    assert "url" in res.json


@pytest.mark.django_db
def test_create_dataset_distribution_with_both_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test distribution"), ("url", "https://test.com/")], files=[("file", "file.csv", b"Test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 400
    assert "file" in res.json
    assert "url" in res.json


@pytest.mark.django_db
def test_create_dataset_distribution_with_empty_file(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test distribution"), ("url", "https://test.com/")], files=[("file", "file.csv", b"")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 400
    assert "file" in res.json


@pytest.mark.django_db
def test_create_dataset_distribution_with_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
        ],
        files=[("file", "file.csv", b"Test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": distribution.description,
        "file": distribution.filename_without_path(),
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": None,
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Test distribution",
        "type": "FILE",
        "url": f"http://{domain}{dataset.get_absolute_url()}",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_create_dataset_distribution_with_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": distribution.description,
        "file": "",
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": None,
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Test distribution",
        "type": "URL",
        "url": "http://test.com/",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
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
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("overwrite", True),
        ],
        files=[("file", distribution.filename_without_path(), b"Test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": distribution.dataset.pk}), params)
    assert distribution.dataset.datasetdistribution_set.count() == 1
    distribution = distribution.dataset.datasetdistribution_set.first()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": distribution.description,
        "file": distribution.filename_without_path(),
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": str(distribution.period_end),
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Test distribution",
        "type": "FILE",
        "url": f"http://{domain}{distribution.dataset.get_absolute_url()}",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_create_non_public_dataset_distribution_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[("title", "Test distribution")], files=[])
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_information_system_distribution_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(subclass=DCATResourceSubclassFactory(name="information_system"))
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[("title", "Test distribution")], files=[])
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_distribution_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": distribution.description,
        "file": "",
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": None,
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Test distribution",
        "type": "URL",
        "url": "http://test.com/",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_create_non_public_dataset_distribution_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(
        reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}), params, expect_errors=True
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_information_system_distribution_with_internal_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test", subclass=DCATResourceSubclassFactory(name="information_system"))
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(
        reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}), params, expect_errors=True
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_put_create_dataset_distribution_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_put_create_non_public_dataset_distribution_open_data_representative(app: DjangoTestApp, access_rights: str):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[("title", "Test distribution")], files=[])
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_put_create_information_system_distribution_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(subclass=DCATResourceSubclassFactory(name="information_system"))
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[("title", "Test distribution")], files=[])
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_put_create_dataset_distribution_without_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(params=[("title", "Test distribution")], files=[])
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 400
    assert "file" in res.json
    assert "url" in res.json


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_both_file_and_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test distribution"), ("url", "https://test.com/")], files=[("file", "file.csv", b"Test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 400
    assert "file" in res.json
    assert "url" in res.json


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_empty_file(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test distribution"), ("url", "https://test.com/")], files=[("file", "file.csv", b"")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert res.status_code == 400
    assert "file" in res.json


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
        ],
        files=[("file", "file.csv", b"Test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": distribution.description,
        "file": distribution.filename_without_path(),
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": None,
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Test distribution",
        "type": "FILE",
        "url": f"http://{domain}{dataset.get_absolute_url()}",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution", kwargs={"datasetId": dataset.pk}), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": distribution.description,
        "file": "",
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": None,
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Test distribution",
        "type": "URL",
        "url": "http://test.com/",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_put_create_dataset_distribution_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}), params)
    assert dataset.datasetdistribution_set.count() == 1
    distribution = dataset.datasetdistribution_set.first()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": distribution.description,
        "file": "",
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": None,
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Test distribution",
        "type": "URL",
        "url": "http://test.com/",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_put_create_non_public_dataset_distribution_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(
        reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}), params, expect_errors=True
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_put_create_information_system_distribution_with_internal_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test", subclass=DCATResourceSubclassFactory(name="information_system"))
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("periodStart", "2022-10-12"),
            ("url", "http://test.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.put(
        reverse("api-distribution-internal", kwargs={"internalId": dataset.internal_id}), params, expect_errors=True
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_update_dataset_distribution_without_api_key(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        expect_errors=True,
    )
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.patch(
        reverse("api-single-distribution", kwargs={"datasetId": another_dataset.pk, "distributionId": distribution.pk}),
        expect_errors=True,
    )
    assert res.status_code == 404


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_update_non_public_dataset_distribution_with_dataset_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    distribution = DatasetDistributionFactory()
    distribution.dataset.access_rights = access_rights
    distribution.dataset.save(update_fields=["access_rights"])
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        expect_errors=True,
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_update_dataset_distribution_with_dataset_id_open_data_representative(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    distribution.dataset.subclass = DCATResourceSubclassFactory(name="information_system")
    distribution.dataset.save(update_fields=["subclass"])
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        expect_errors=True,
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_update_dataset_distribution_with_wrong_internal_id(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    another_dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.patch(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": another_dataset.internal_id, "distributionId": distribution.pk},
        ),
        expect_errors=True,
    )
    assert res.status_code == 404


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_update_non_public_dataset_distribution_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    distribution = DatasetDistributionFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Updated title"),
            ("description", "Updated description"),
            ("region", "Geo"),
            ("municipality", "Location"),
        ],
        files=[("file", "updated_file.csv", b"test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": dataset.internal_id, "distributionId": distribution.pk},
        ),
        params,
        expect_errors=True,
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_update_information_system_distribution_with_internal_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test", subclass=DCATResourceSubclassFactory(name="information_system"))
    distribution = DatasetDistributionFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Updated title"),
            ("description", "Updated description"),
            ("region", "Geo"),
            ("municipality", "Location"),
        ],
        files=[("file", "updated_file.csv", b"test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": dataset.internal_id, "distributionId": distribution.pk},
        ),
        params,
        expect_errors=True,
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_update_dataset_distribution_with_both_file_and_url(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test distribution"), ("url", "http://example.com/")], files=[("file", "file.csv", b"Test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        params,
        expect_errors=True,
    )
    assert res.status_code == 400
    assert "file" in res.json
    assert "url" in res.json


@pytest.mark.django_db
def test_update_dataset_distribution_with_empty_file(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Test distribution"),
        ],
        files=[("file", "file.csv", b"")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        params,
        expect_errors=True,
    )
    assert res.status_code == 400
    assert "file" in res.json


@pytest.mark.django_db
def test_update_dataset_distribution_with_not_allowed_file(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Updated title"),
            ("description", "Updated description"),
            ("region", "Geo"),
            ("municipality", "Location"),
        ],
        files=[("file", "updated_file.html", b"test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        params,
        expect_errors=True,
    )
    assert "file" in res.json


@pytest.mark.django_db
def test_update_dataset_distribution_with_file(app: DjangoTestApp):
    domain = Site.objects.get_current().domain
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Updated title"),
            ("description", "Updated description"),
            ("region", "Geo"),
            ("municipality", "Location"),
        ],
        files=[("file", "updated_file.csv", b"test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        params,
    )
    distribution.refresh_from_db()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": "Updated description",
        "file": distribution.filename_without_path(),
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": str(distribution.period_end),
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Updated title",
        "type": "FILE",
        "url": f"http://{domain}{distribution.dataset.get_absolute_url()}",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_update_dataset_distribution_with_url(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(distribution.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=distribution.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Updated title"),
            ("description", "Updated description"),
            ("region", "Geo"),
            ("municipality", "Location"),
            ("url", "http://example.com/"),
        ],
        files=[],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        params,
    )
    distribution.set_current_language("lt")
    assert res.json == {
        "description": "Updated description",
        "file": "",
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": str(distribution.period_end),
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Updated title",
        "type": "URL",
        "url": "http://example.com/",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
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
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[
            ("title", "Updated title"),
            ("description", "Updated description"),
            ("region", "Geo"),
            ("municipality", "Location"),
        ],
        files=[("file", "updated_file.csv", b"test")],
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.patch(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": dataset.internal_id, "distributionId": distribution.pk},
        ),
        params,
    )
    distribution.refresh_from_db()
    distribution.set_current_language("lt")
    assert res.json == {
        "description": "Updated description",
        "file": distribution.filename_without_path(),
        "id": distribution.pk,
        "issued": distribution.issued,
        "periodEnd": str(distribution.period_end),
        "periodStart": str(distribution.period_start),
        "geo_location": "Geo Location",
        "title": "Updated title",
        "type": "FILE",
        "url": f"http://{domain}{dataset.get_absolute_url()}",
        "version": distribution.distribution_version,
        "upload_to_storage": distribution.upload_to_storage,
    }


@pytest.mark.django_db
def test_delete_dataset_distribution_without_api_key(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    res = app.delete(
        reverse(
            "api-single-distribution", kwargs={"datasetId": distribution.dataset.pk, "distributionId": distribution.pk}
        ),
        expect_errors=True,
    )
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse("api-single-distribution", kwargs={"datasetId": another_dataset.pk, "distributionId": distribution.pk}),
        expect_errors=True,
    )
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": another_dataset.internal_id, "distributionId": distribution.pk},
        ),
        expect_errors=True,
    )
    assert res.status_code == 404


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_delete_non_public_dataset_distribution_with_dataset_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    distribution = DatasetDistributionFactory()
    dataset = distribution.dataset
    dataset.access_rights = access_rights
    dataset.save(update_fields=["access_rights"])
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse("api-single-distribution", kwargs={"datasetId": dataset.pk, "distributionId": distribution.pk}),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetdistribution_set.count() == 1


@pytest.mark.django_db
def test_delete_dataset_distribution_with_dataset_id_open_data_representative(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    dataset = distribution.dataset
    dataset.subclass = DCATResourceSubclassFactory(name="information_system")
    dataset.save(update_fields=["subclass"])
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse("api-single-distribution", kwargs={"datasetId": dataset.pk, "distributionId": distribution.pk}),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetdistribution_set.count() == 1


@pytest.mark.django_db
def test_delete_dataset_distribution_with_dataset_id(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    app.delete(reverse("api-single-distribution", kwargs={"datasetId": dataset.pk, "distributionId": distribution.pk}))
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    app.delete(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": dataset.internal_id, "distributionId": distribution.pk},
        )
    )
    assert dataset.datasetdistribution_set.count() == 0


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_delete_non_public_dataset_distribution_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    distribution = DatasetDistributionFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": dataset.internal_id, "distributionId": distribution.pk},
        ),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetdistribution_set.count() == 1


@pytest.mark.django_db
def test_delete_information_system_distribution_with_internal_id_open_data_representative(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test", subclass=DCATResourceSubclassFactory(name="information_system"))
    distribution = DatasetDistributionFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse(
            "api-single-distribution-internal",
            kwargs={"internalId": dataset.internal_id, "distributionId": distribution.pk},
        ),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetdistribution_set.count() == 1


@pytest.mark.django_db
def test_get_dataset_structures_without_api_key(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    res = app.get(reverse("api-structure", kwargs={"datasetId": structure.dataset.pk}), expect_errors=True)
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-structure", kwargs={"datasetId": structure.dataset.pk}))
    assert res.json == [
        {
            "created": timezone.localtime(structure.created).isoformat(),
            "filename": structure.filename_without_path(),
            "id": structure.pk,
            "size": structure.size,
            "title": structure.title,
        }
    ]


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_get_non_public_dataset_structures_on_non_public_datasets_with_dataset_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    structure = DatasetStructureFactory()
    DatasetStructureFactory()
    structure.dataset.access_rights = access_rights
    structure.dataset.save(update_fields=["access_rights"])
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-structure", kwargs={"datasetId": structure.dataset.pk}), expect_errors=True)
    assert res.status_code == 403


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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-structure-internal", kwargs={"internalId": dataset.internal_id}))
    assert res.json == [
        {
            "created": timezone.localtime(structure.created).isoformat(),
            "filename": structure.filename_without_path(),
            "id": structure.pk,
            "size": structure.size,
            "title": structure.title,
        }
    ]


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_get_non_public_dataset_structures_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    DatasetStructureFactory(dataset=dataset)
    DatasetStructureFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-structure-internal", kwargs={"internalId": dataset.internal_id}), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_structures_without_api_key(app: DjangoTestApp):
    dataset = DatasetFactory()
    res = app.post(reverse("api-structure", kwargs={"datasetId": dataset.pk}), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_create_dataset_structure_with_errors(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.post(reverse("api-structure", kwargs={"datasetId": dataset.pk}), expect_errors=True)
    assert dataset.datasetstructure_set.count() == 0
    assert "file" in res.json
    assert "title" in res.json


@pytest.mark.django_db
def test_create_dataset_structure_with_not_allowed_file(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test structure")], files=[("file", "file.svg", b"test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-structure", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    assert "file" in res.json


@pytest.mark.django_db
def test_create_dataset_structure_with_dataset_id(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test structure")], files=[("file", "file.csv", b"test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-structure", kwargs={"datasetId": dataset.pk}), params)
    dataset.refresh_from_db()
    assert dataset.datasetstructure_set.count() == 1
    structure = dataset.datasetstructure_set.first()
    assert dataset.current_structure == structure
    assert res.json == {
        "created": timezone.localtime(structure.created).isoformat(),
        "filename": structure.filename_without_path(),
        "id": structure.pk,
        "size": structure.size,
        "title": structure.title,
    }


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_create_non_public_dataset_structure_with_dataset_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test structure")], files=[("file", "file.csv", b"test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-structure", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.django_db
def test_create_information_system_structure_non_public_dataset_with_dataset_id_open_data_representative(
    app: DjangoTestApp,
):
    dataset = DatasetFactory(subclass=DCATResourceSubclassFactory(name="information_system"))
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test structure")], files=[("file", "file.csv", b"test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-structure", kwargs={"datasetId": dataset.pk}), params, expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.django_db
def test_create_dataset_structure_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test structure")], files=[("file", "file.csv", b"test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(reverse("api-structure-internal", kwargs={"internalId": dataset.internal_id}), params)
    dataset.refresh_from_db()
    assert dataset.datasetstructure_set.count() == 1
    structure = dataset.datasetstructure_set.first()
    assert dataset.current_structure == structure
    assert res.json == {
        "created": timezone.localtime(structure.created).isoformat(),
        "filename": structure.filename_without_path(),
        "id": structure.pk,
        "size": structure.size,
        "title": structure.title,
    }


@pytest.mark.django_db
@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
def test_create_non_public_dataset_structure_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test structure")], files=[("file", "file.csv", b"test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(
        reverse("api-structure-internal", kwargs={"internalId": dataset.internal_id}), params, expect_errors=True
    )
    dataset.refresh_from_db()
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.django_db
def test_create_information_system_structure_non_public_dataset_with_internal_id_open_data_representative(
    app: DjangoTestApp,
):
    dataset = DatasetFactory(internal_id="test", subclass=DCATResourceSubclassFactory(name="information_system"))
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    content_type, params = app.encode_multipart(
        params=[("title", "Test structure")], files=[("file", "file.csv", b"test")]
    )
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test", "CONTENT_TYPE": content_type})
    res = app.post(
        reverse("api-structure-internal", kwargs={"internalId": dataset.internal_id}), params, expect_errors=True
    )
    dataset.refresh_from_db()
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.django_db
def test_delete_dataset_structures_without_api_key(app: DjangoTestApp):
    structure = DatasetStructureFactory()
    res = app.delete(
        reverse("api-single-structure", kwargs={"datasetId": structure.dataset.pk, "structureId": structure.pk}),
        expect_errors=True,
    )
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse("api-single-structure", kwargs={"datasetId": another_dataset.pk, "structureId": structure.pk}),
        expect_errors=True,
    )
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse(
            "api-single-structure-internal",
            kwargs={"internalId": another_dataset.internal_id, "structureId": structure.pk},
        ),
        expect_errors=True,
    )
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
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    app.delete(reverse("api-single-structure", kwargs={"datasetId": dataset.pk, "structureId": structure.pk}))
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_delete_non_public_dataset_structure_with_dataset_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    structure = DatasetStructureFactory()
    dataset = structure.dataset
    dataset.access_rights = access_rights
    dataset.save(update_fields=["access_rights"])
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse("api-single-structure", kwargs={"datasetId": dataset.pk, "structureId": structure.pk}),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 1


@pytest.mark.django_db
def test_delete_information_system_structure_with_dataset_id_open_data_representative(
    app: DjangoTestApp,
):
    structure = DatasetStructureFactory()
    dataset = structure.dataset
    dataset.subclass = DCATResourceSubclassFactory(name="information_system")
    dataset.save(update_fields=["subclass"])
    ct = ContentType.objects.get_for_model(dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse("api-single-structure", kwargs={"datasetId": dataset.pk, "structureId": structure.pk}),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 1


@pytest.mark.django_db
def test_delete_dataset_structure_with_internal_id(app: DjangoTestApp):
    dataset = DatasetFactory(internal_id="test")
    structure = DatasetStructureFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    app.delete(
        reverse(
            "api-single-structure-internal", kwargs={"internalId": dataset.internal_id, "structureId": structure.pk}
        )
    )
    assert dataset.datasetstructure_set.count() == 0


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_delete_non_public_dataset_structure_with_internal_id_open_data_representative(
    app: DjangoTestApp, access_rights: str
):
    dataset = DatasetFactory(internal_id="test", access_rights=access_rights)
    structure = DatasetStructureFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse(
            "api-single-structure-internal", kwargs={"internalId": dataset.internal_id, "structureId": structure.pk}
        ),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 1


@pytest.mark.django_db
def test_delete_information_system_structure_with_internal_id_open_data_representative(
    app: DjangoTestApp,
):
    dataset = DatasetFactory(internal_id="test", subclass=DCATResourceSubclassFactory(name="information_system"))
    structure = DatasetStructureFactory(dataset=dataset)
    ct = ContentType.objects.get_for_model(structure.dataset.organization)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.organization.pk,
    )
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(
        reverse(
            "api-single-structure-internal", kwargs={"internalId": dataset.internal_id, "structureId": structure.pk}
        ),
        expect_errors=True,
    )
    assert res.status_code == 403
    assert dataset.datasetstructure_set.count() == 1


@pytest.mark.django_db
def test_create_model_statistics(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    user = UserFactory(is_staff=True)
    representative = RepresentativeFactory(content_type=ct, object_id=organization.pk, user=user)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.post(
        reverse("api-download-stats-internal"),
        {
            "source": "get.data.gov.lt",
            "model": "naujas_modelis",
            "format": "excel",
            "time": datetime.now(),
            "requests": 100,
            "objects": 10,
        },
        expect_errors=False,
    )
    assert res.json == {
        "source": "get.data.gov.lt",
        "model": "naujas_modelis",
        "format": "excel",
        "time": timezone.localtime(ModelDownloadStats.objects.first().created).isoformat(),
        "requests": 100,
        "objects": 10,
    }


@pytest.mark.django_db
def test_edp_dcat_ap_rdf(app: DjangoTestApp):
    Dataset.objects.all().delete()
    iana = "http://www.iana.org/assignments"
    po = "http://publications.europa.eu/resource/authority"

    dataset = DatasetFactory(
        title={
            "lt": "Testas1",
            "en": "Test1",
        },
        description={
            "lt": "Duomenų rinkinio aprašymas.",
            "en": "Dataset description.",
        },
        published=datetime(2016, 8, 1),
        frequency=FrequencyFactory(uri=f"{po}/frequency/IRREG"),
        category=[
            CategoryFactory(title="Energy"),
            CategoryFactory(
                title="Environment",
                uri=f"{po}/data-theme/ENVI",
            ),
        ],
        organization=OrganizationFactory(
            title="Data Enterprise",
            email="data@example.com",
        ),
        access_rights=Dataset.PUBLIC,
    )
    dist1 = DatasetDistributionFactory(
        dataset=dataset,
        title="CSV failas",
        description="Atviras duomenų šaltinis.",
        format=FileFormat(
            uri=f"{po}/file-type/CSV",
            media_type_uri=f"{iana}/media-types/text/csv",
        ),
        licence=LicenceFactory(url=f"{po}/licence/CC_BY_4_0"),
        conditions="platinimo sąlygos",
    )
    dist2 = DatasetDistributionFactory(
        dataset=dataset,
        title="Duomenų teikimo paslauga",
        description="Universali duomenų teikimo paslauga.",
        format=FileFormat(
            extension="UAPI",
            uri=f"{po}/file-type/JSON",
            media_type_uri=f"{iana}/media-types/application/json",
        ),
        licence=LicenceFactory(url=f"{po}/licence/CC_BY_4_0"),
        conditions="platinimo sąlygos",
    )

    res = app.get("/edp/dcat-ap.rdf")

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f"""\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://localhost"
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
    <dcat:Dataset rdf:about="http://localhost/datasets/{dataset.id}/">
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/resource/{dist1.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">CSV failas</dct:title>
                <dct:description xml:lang="lt">Atviras duomenų šaltinis.</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="http://localhost{dist1.file.url}"/>
                <dcat:downloadURL rdf:resource="http://localhost{dist1.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/resource/{dist2.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/WEB_SERVICE"/>
                <dct:title xml:lang="lt">Duomenų teikimo paslauga</dct:title>
                <dct:description xml:lang="lt">Universali duomenų teikimo paslauga.</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="http://localhost{dist2.file.url}"/>
                <dcat:downloadURL rdf:resource="http://localhost{dist2.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
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
</rdf:RDF>"""
    )


@pytest.mark.django_db
def test_get_all_datasets_publisher_exclusive(app: DjangoTestApp):
    """
    If API access is granted to 1 dataset,
    get all should be forbidden
    """
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    dataset = DatasetFactory(is_public=False, organization=org)
    DatasetFactory(organization=org)
    DatasetFactory(organization=org)
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk, user=None, organization=publisher_org)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-dataset"), expect_errors=True)
    dataset.refresh_from_db()
    assert res.status_code == 403


@pytest.mark.django_db
def test_get_all_datasets_publisher(app: DjangoTestApp):
    """
    If API access is granted to an organization,
    get all should return all the datasets from that organization
    """
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    ds1 = DatasetFactory(is_public=False, organization=org)
    ds2 = DatasetFactory(organization=org)
    DatasetFactory()
    ct = ContentType.objects.get_for_model(org)
    representative = RepresentativeFactory(content_type=ct, object_id=org.pk, user=None, organization=publisher_org)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.get(reverse("api-dataset"), expect_errors=True)
    assert len(res.json) == 2
    assert {int(ds["id"]) for ds in res.json} == {ds1.pk, ds2.pk}


@pytest.mark.django_db
def test_get_dataset_publisher(app: DjangoTestApp):
    """
    If API access is granted to a single dataset,
    access should only be granted to that dataset.
    """
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    ds1 = DatasetFactory(is_public=False, organization=org)
    ds2 = DatasetFactory(organization=org)
    ct = ContentType.objects.get_for_model(ds1)
    representative = RepresentativeFactory(content_type=ct, object_id=ds1.pk, user=None, organization=publisher_org)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(reverse("api-single-dataset", kwargs={"datasetId": ds2.pk}), expect_errors=True)
    assert res.status_code == 403

    res = app.get(reverse("api-single-dataset", kwargs={"datasetId": ds1.pk}))
    assert int(res.json["id"]) == ds1.pk


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_get_dataset_publisher_non_public_datasets(app: DjangoTestApp, access_rights: str):
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    ds1 = DatasetFactory(is_public=False, organization=org, access_rights=access_rights)
    ds2 = DatasetFactory(organization=org, access_rights=access_rights)
    ct = ContentType.objects.get_for_model(ds1)
    representative = RepresentativeFactory(content_type=ct, object_id=ds1.pk, user=None, organization=publisher_org)
    APIKeyFactory(representative=representative)
    app.extra_environ.update({"HTTP_AUTHORIZATION": "ApiKey test"})
    res = app.delete(reverse("api-single-dataset", kwargs={"datasetId": ds2.pk}), expect_errors=True)
    assert res.status_code == 403

    res = app.get(reverse("api-single-dataset", kwargs={"datasetId": ds1.pk}), expect_errors=True)
    assert res.status_code == 404


class EdpDcatApRestrictedRdfTests(TestCase):
    def test_edp_dcat_ap_restricted_rdf_returns_rdf(self):
        organization = OrganizationFactory()
        Dataset.objects.create(
            title="Restricted Dataset",
            access_rights=Dataset.RESTRICTED,
            deleted=None,
            deleted_on=None,
            organization_id=organization.pk,
        )

        response = self.client.get(reverse("edp-dcat-ap-restricted-rdf"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/rdf+xml")
        self.assertIn(b"Restricted Dataset", response.content)

    def test_edp_dcat_ap_restricted_rdf_with_no_datasets(self):
        response = self.client.get(reverse("edp-dcat-ap-restricted-rdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/rdf+xml")
        self.assertNotIn(b"<dcat:Dataset>", response.content)

    def test_edp_dcat_ap_restricted_rdf_excludes_public(self):
        organization = OrganizationFactory()
        Dataset.objects.create(
            title="Public Dataset",
            access_rights="public",  # Not Dataset.RESTRICTED
            deleted=None,
            deleted_on=None,
            organization_id=organization.pk,
        )
        response = self.client.get(reverse("edp-dcat-ap-restricted-rdf"))
        self.assertNotIn(b"Public Dataset", response.content)


class EdpDcatApPublicRdfTests(TestCase):
    def test_edp_dcat_ap_public_rdf_returns_rdf(self):
        organization = OrganizationFactory()
        Dataset.objects.create(
            title="Public Dataset",
            access_rights=Dataset.PUBLIC,
            deleted=None,
            deleted_on=None,
            organization_id=organization.pk,
        )

        response = self.client.get(reverse("edp-dcat-ap-rdf"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/rdf+xml")
        self.assertIn(b"Public Dataset", response.content)

    def test_edp_dcat_ap_public_rdf_with_no_datasets(self):
        response = self.client.get(reverse("edp-dcat-ap-rdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/rdf+xml")
        self.assertNotIn(b"<dcat:Dataset>", response.content)

    def test_edp_dcat_ap_public_rdf_excludes_restricted(self):
        organization = OrganizationFactory()
        Dataset.objects.create(
            title="Restricted Dataset",
            access_rights=Dataset.RESTRICTED,  # Not Dataset.PUBLIC
            deleted=None,
            deleted_on=None,
            organization_id=organization.pk,
        )
        response = self.client.get(reverse("edp-dcat-ap-rdf"))
        self.assertNotIn(b"Restricted Dataset", response.content)

    def test_edp_dcat_ap_rdf_homepage_for_information_system_subclass(self):
        DatasetFactory(
            subclass=DCATResourceSubclassFactory(name="information_system"), landing_page="https://example.com"
        )

        response = self.client.get(reverse("edp-dcat-ap-rdf"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/rdf+xml")
        self.assertNotIn(b"dcat:landingPage", response.content)
        self.assertIn(b"foaf:homepage", response.content)


@pytest.mark.django_db
def test_edp_dcat_ap_rdf_hvd_dataset(app: DjangoTestApp):
    Dataset.objects.all().delete()
    hvd_group = DatasetGroupFactory(name="hvd")
    hvd_group.set_current_language("lt")
    hvd_group.title = "Didelės vertės rinkiniai"
    hvd_group.save()
    parent_category = CategoryFactory(
        title="Environment",
        uri="http://publications.europa.eu/resource/authority/data-theme/ENVI",
    )
    hvd_category = parent_category.add_child(
        instance=CategoryFactory.build(
            title="Earth observation and environment",
        )
    )
    DatasetGroupCategoryUriFactory(group=hvd_group, category=hvd_category, uri="http://data.europa.eu/bna/c_dd313021")

    dataset = DatasetFactory(
        title={
            "lt": "Testas1",
            "en": "Test1",
        },
        description={
            "lt": "Duomenų rinkinio aprašymas.",
            "en": "Dataset description.",
        },
        published=datetime(2016, 8, 1),
        frequency=FrequencyFactory(uri="http://publications.europa.eu/resource/authority/frequency/IRREG"),
        category=[hvd_category],
        organization=OrganizationFactory(
            title="Data Enterprise",
            email="data@example.com",
        ),
        access_rights=Dataset.PUBLIC,
        is_hvd=True,
    )

    res = app.get("/edp/dcat-ap.rdf")

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f"""\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://localhost"
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
    <dcat:Dataset rdf:about="http://localhost/datasets/{dataset.id}/">
        <dct:title xml:lang="en">Test1</dct:title>
        <dct:description xml:lang="en">Dataset description.</dct:description>
        <dct:title xml:lang="lt">Testas1</dct:title>
        <dct:description xml:lang="lt">Duomenų rinkinio aprašymas.</dct:description>
        <dcatap:applicableLegislation>
            <eli:LegalResource rdf:about="http://data.europa.eu/eli/reg_impl/2023/138/oj"/>
        </dcatap:applicableLegislation>
        <dcatap:hvdCategory>
            <skos:Concept rdf:about="http://data.europa.eu/bna/c_dd313021"/>
        </dcatap:hvdCategory>
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
    </dcat:Dataset>
</rdf:RDF>"""
    )


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("Hello\tWorld", "Hello&#x9;World"),
        ("Col1\tCol2\tCol3", "Col1&#x9;Col2&#x9;Col3"),
        ("No tabs here", "No tabs here"),
        ("", ""),
    ],
)
def test_encode_xml_control_chars(input_str, expected):
    assert _encode_xml_control_chars(input_str) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights, url_name",
    [
        (Dataset.PUBLIC, "edp-dcat-ap-rdf"),
        (Dataset.RESTRICTED, "edp-dcat-ap-restricted-rdf"),
    ],
)
def test_edp_dcat_ap_rdf_encodes_tabs_in_rights_statement(app: DjangoTestApp, access_rights, url_name):
    organization = OrganizationFactory()
    dataset = Dataset.objects.create(
        title="Dataset with tabs",
        access_rights=access_rights,
        deleted=None,
        deleted_on=None,
        organization_id=organization.pk,
    )
    DatasetDistributionFactory(
        dataset=dataset,
        conditions="Legal document\thttps://example.com/legal",
    )

    response = app.get(reverse(url_name))

    assert response.status_code == 200
    assert b"&#x9;" in response.content
    assert b"Legal document\t" not in response.content
