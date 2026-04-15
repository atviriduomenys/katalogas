from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.tasks import update_spinta_distribution_dates


@pytest.mark.django_db
def test_task_runs_without_errors():
    with patch("vitrina.resources.tasks._fetch_spinta_last_modified", return_value=None):
        update_spinta_distribution_dates()


@pytest.mark.django_db
def test_task_updates_data_last_updated():
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    distribution.data_last_updated = None
    distribution.save(update_fields=["data_last_updated"])

    new_date = timezone.now()
    with patch("vitrina.resources.tasks._fetch_spinta_last_modified", return_value=new_date):
        update_spinta_distribution_dates()

    distribution.refresh_from_db()
    assert distribution.data_last_updated == new_date


@pytest.mark.django_db
def test_task_skips_recently_checked_distributions():
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    distribution.data_last_updated = timezone.now()
    distribution.save(update_fields=["data_last_updated"])

    with patch("vitrina.resources.tasks._fetch_spinta_last_modified") as mock_fetch:
        update_spinta_distribution_dates()
        mock_fetch.assert_not_called()


@pytest.mark.django_db
def test_task_does_not_update_when_spinta_returns_older_date():
    dataset = DatasetFactory()
    distribution = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    current_date = timezone.now() - timedelta(days=1)
    distribution.data_last_updated = current_date
    distribution.save(update_fields=["data_last_updated"])

    older_date = current_date - timedelta(days=5)
    with patch("vitrina.resources.tasks._fetch_spinta_last_modified", return_value=older_date):
        update_spinta_distribution_dates()

    distribution.refresh_from_db()
    assert distribution.data_last_updated == current_date
