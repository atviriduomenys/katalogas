from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.tasks import _fetch_spinta_last_modified, update_spinta_distribution_dates


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


def _mock_distribution_with_models(*full_names: str) -> MagicMock:
    distribution = MagicMock()
    distribution.pk = 42
    models = [MagicMock(full_name=name) for name in full_names]
    distribution.dataset.model_set.all.return_value.__iter__.return_value = iter(models)
    distribution.dataset.model_set.all.return_value.exists.return_value = bool(models)
    return distribution


def test_fetch_uses_changes_last_row_endpoint():
    # Regression: :changes silently ignores sort()/limit() and returns _cid ASC,
    # so the task must use :changes/-1/ to read the latest change, not a sort+limit query.
    distribution = _mock_distribution_with_models("gov/vmi/ja_nepriemokos/NepriemokosSuma")

    with patch("vitrina.resources.tasks.get_data_from_spinta") as mock_get:
        mock_get.return_value = {"_data": [{"_created": "2026-05-14T06:12:15.722841"}]}
        _fetch_spinta_last_modified(distribution)

    mock_get.assert_called_once()
    args, _kwargs = mock_get.call_args
    assert args[0] == "gov/vmi/ja_nepriemokos/NepriemokosSuma"
    assert args[1] == ":changes/-1/"


def test_fetch_returns_max_across_all_models():
    # A dataset can have multiple models; data_last_updated should reflect the
    # most recent change across all of them, not just the first model.
    distribution = _mock_distribution_with_models("ns/ModelA", "ns/ModelB", "ns/ModelC")

    responses = {
        "ns/ModelA": {"_data": [{"_created": "2026-01-01T00:00:00"}]},
        "ns/ModelB": {"_data": [{"_created": "2026-05-14T06:12:15"}]},  # newest
        "ns/ModelC": {"_data": [{"_created": "2025-06-01T00:00:00"}]},
    }

    with patch("vitrina.resources.tasks.get_data_from_spinta") as mock_get:
        mock_get.side_effect = lambda name, *a, **kw: responses[name]
        result = _fetch_spinta_last_modified(distribution)

    assert mock_get.call_count == 3
    assert result.isoformat().startswith("2026-05-14T06:12:15")


def test_fetch_tolerates_errors_from_individual_models():
    # If one model's :changes query errors, the task should still use the
    # newest timestamp from the models that did respond.
    distribution = _mock_distribution_with_models("ns/Broken", "ns/Working")

    responses = {
        "ns/Broken": {"errors": ["some upstream failure"]},
        "ns/Working": {"_data": [{"_created": "2026-05-14T06:12:15"}]},
    }

    with patch("vitrina.resources.tasks.get_data_from_spinta") as mock_get:
        mock_get.side_effect = lambda name, *a, **kw: responses[name]
        result = _fetch_spinta_last_modified(distribution)

    assert result.isoformat().startswith("2026-05-14T06:12:15")
