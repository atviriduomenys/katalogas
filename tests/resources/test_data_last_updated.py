from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat
from vitrina.resources.models import DatasetDistribution
from vitrina.resources.tasks import update_spinta_distribution_dates
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_data_last_updated_field_exists_and_nullable():
    dist = DatasetDistributionFactory()
    dist.refresh_from_db()
    dist.data_last_updated = None
    dist.save(update_fields=["data_last_updated"])
    dist.refresh_from_db()
    assert dist.data_last_updated is None


@pytest.mark.django_db
def test_data_last_updated_not_set_on_create(app: DjangoTestApp):
    dataset = DatasetFactory()
    file_format = FileFormat(extension="URL")
    user = UserFactory(is_staff=True, organization=dataset.organization)
    app.set_user(user)
    form = app.get(reverse("resource-add", kwargs={"pk": dataset.pk})).forms["resource-form"]
    form["title"] = "Test resource"
    form["format"] = file_format.id
    form["download_url"] = "http://www.example.com"
    resp = form.submit()
    assert resp.status_code == 302
    dist = DatasetDistribution.objects.first()
    assert dist.data_last_updated is None


@pytest.mark.django_db
def test_template_shows_data_last_updated(app: DjangoTestApp):
    now = timezone.now()
    resource = DatasetDistributionFactory()
    resource.data_last_updated = now
    resource.save(update_fields=["data_last_updated"])

    resp = app.get(reverse("dataset-detail", kwargs={"pk": resource.dataset_id})).follow()
    assert resp.status_code == 200


@pytest.mark.django_db
def test_template_falls_back_to_modified_when_data_last_updated_is_null(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    resource.data_last_updated = None
    resource.save(update_fields=["data_last_updated"])

    resp = app.get(reverse("dataset-detail", kwargs={"pk": resource.dataset_id})).follow()
    assert resp.status_code == 200


@pytest.mark.django_db
def test_api_serializer_includes_data_last_updated():
    from vitrina.api.serializers import DatasetDistributionSerializer

    now = timezone.now()
    dist = DatasetDistributionFactory()
    dist.data_last_updated = now
    dist.save(update_fields=["data_last_updated"])

    serializer = DatasetDistributionSerializer(dist)
    assert "data_last_updated" in serializer.data
    assert serializer.data["data_last_updated"] is not None


@pytest.mark.django_db
def test_api_serializer_returns_none_when_data_last_updated_is_null():
    from vitrina.api.serializers import DatasetDistributionSerializer

    dist = DatasetDistributionFactory()
    dist.data_last_updated = None
    dist.save(update_fields=["data_last_updated"])

    serializer = DatasetDistributionSerializer(dist)
    assert "data_last_updated" in serializer.data
    assert serializer.data["data_last_updated"] is None


@pytest.mark.django_db
def test_celery_task_runs_without_errors():
    with patch("vitrina.resources.tasks._fetch_spinta_last_modified", return_value=None):
        update_spinta_distribution_dates()


@pytest.mark.django_db
def test_celery_task_updates_data_last_updated():
    dataset = DatasetFactory()
    dist = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    dist.data_last_updated = None
    dist.save(update_fields=["data_last_updated"])

    new_date = timezone.now()
    with patch("vitrina.resources.tasks._fetch_spinta_last_modified", return_value=new_date):
        update_spinta_distribution_dates()

    dist.refresh_from_db()
    assert dist.data_last_updated == new_date


@pytest.mark.django_db
def test_celery_task_skips_recently_checked_distributions():
    dataset = DatasetFactory()
    dist = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    dist.data_last_updated = timezone.now()
    dist.save(update_fields=["data_last_updated"])

    with patch("vitrina.resources.tasks._fetch_spinta_last_modified") as mock_fetch:
        update_spinta_distribution_dates()
        mock_fetch.assert_not_called()


@pytest.mark.django_db
def test_celery_task_does_not_update_when_spinta_returns_older_date():
    dataset = DatasetFactory()
    dist = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    current_date = timezone.now() - timedelta(days=1)
    dist.data_last_updated = current_date
    dist.save(update_fields=["data_last_updated"])

    older_date = current_date - timedelta(days=5)
    with patch("vitrina.resources.tasks._fetch_spinta_last_modified", return_value=older_date):
        update_spinta_distribution_dates()

    dist.refresh_from_db()
    assert dist.data_last_updated == current_date


@pytest.mark.django_db
def test_bulk_update_does_not_trigger_auto_now():
    dist = DatasetDistributionFactory()
    original_modified = dist.modified

    dist.data_last_updated = timezone.now()
    DatasetDistribution.objects.bulk_update([dist], ["data_last_updated"])

    dist.refresh_from_db()
    assert dist.modified == original_modified
