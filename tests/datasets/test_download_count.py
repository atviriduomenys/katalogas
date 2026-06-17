import os
from unittest import mock

import pytest
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory


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
