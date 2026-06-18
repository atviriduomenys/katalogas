import os
from unittest import mock

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.factories import MetadataFactory, ModelFactory, VersionFactory


def _setup_dynamic_resource_dataset():
    dataset = DatasetFactory(metadata="TestModel")
    DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="TestModel",
        metadata_version=version,
    )
    return dataset, version


@pytest.mark.django_db
def test_download_count_defaults_to_zero():
    dataset = DatasetFactory()
    assert dataset.get_download_count() == 0


@pytest.mark.django_db
def test_get_download_count_returns_field_value():
    dataset = DatasetFactory(download_count=7)
    assert dataset.get_download_count() == 7


@pytest.mark.django_db
def test_rdf_download_increments_count(client):
    dataset = DatasetFactory()

    response = client.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert response.status_code == 200
    dataset.refresh_from_db()
    assert dataset.download_count == 1


@pytest.mark.django_db
def test_distribution_file_download_increments_count(client):
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(dataset=dataset)

    response = client.get(reverse("dataset-distribution-download", args=[dataset.pk, distribution.pk]))

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")
    dataset.refresh_from_db()
    assert dataset.download_count == 1


@pytest.mark.django_db
def test_distribution_external_link_download_increments_and_redirects(client):
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(dataset=dataset, file=None, download_url="https://example.com/data.csv")

    response = client.get(reverse("dataset-distribution-download", args=[dataset.pk, distribution.pk]))

    assert response.status_code == 302
    assert response["Location"] == "https://example.com/data.csv"
    dataset.refresh_from_db()
    assert dataset.download_count == 1


@pytest.mark.django_db
def test_distribution_download_uses_access_url_when_no_file_or_download_url(client):
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(
        dataset=dataset, file=None, download_url="", access_url="https://example.com/page"
    )

    response = client.get(reverse("dataset-distribution-download", args=[dataset.pk, distribution.pk]))

    assert response.status_code == 302
    assert response["Location"] == "https://example.com/page"
    dataset.refresh_from_db()
    assert dataset.download_count == 1


@pytest.mark.django_db
def test_rdf_download_is_not_counted_when_rendering_fails(client):
    dataset = DatasetFactory()

    with mock.patch("vitrina.datasets.views.render_rdf_response", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            client.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    dataset.refresh_from_db()
    assert dataset.download_count == 0


@pytest.mark.django_db
def test_distribution_file_download_is_not_counted_when_file_is_missing(client):
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(dataset=dataset)
    os.remove(distribution.file.file.path)

    response = client.get(reverse("dataset-distribution-download", args=[dataset.pk, distribution.pk]))

    assert response.status_code == 404
    dataset.refresh_from_db()
    assert dataset.download_count == 0


@pytest.mark.django_db
def test_dynamic_resource_download_increments_and_redirects_to_spinta(client):
    dataset, version = _setup_dynamic_resource_dataset()

    response = client.get(
        reverse(
            "dataset-dynamic-resource-download",
            kwargs={"pk": dataset.pk, "version_id": version.pk, "distribution_name": "TestModel", "format": "json"},
        )
    )

    assert response.status_code == 302
    assert response["Location"].startswith(SPINTA_SERVER_URL)
    assert response["Location"].endswith("/:all/:format/json")
    dataset.refresh_from_db()
    assert dataset.download_count == 1


@pytest.mark.django_db
def test_dynamic_resource_download_returns_404_for_unknown_resource(client):
    dataset, version = _setup_dynamic_resource_dataset()

    response = client.get(
        reverse(
            "dataset-dynamic-resource-download",
            kwargs={
                "pk": dataset.pk,
                "version_id": version.pk,
                "distribution_name": "DoesNotExist",
                "format": "csv",
            },
        )
    )

    assert response.status_code == 404
    dataset.refresh_from_db()
    assert dataset.download_count == 0
