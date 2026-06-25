import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.statistics.models import DatasetStats
from vitrina.structure.factories import ModelFactory


@pytest.mark.django_db
def test_build_dataset_stats_stores_object_count_at_published_date():
    from vitrina.statistics.services import build_dataset_stats

    dataset = DatasetFactory(published=datetime(2023, 5, 10, 10, 0, 0, tzinfo=timezone.utc))
    ModelFactory(dataset=dataset)
    response = Mock(content=json.dumps({"_data": [{"count()": 42}]}))
    with patch("vitrina.statistics.services.requests.get", return_value=response) as mock_get:
        build_dataset_stats()
    assert mock_get.called
    stat = DatasetStats.objects.get(dataset_id=dataset.pk, created=dataset.published.date())
    assert stat.object_count == 42


@pytest.mark.django_db
def test_build_dataset_stats_preserves_object_count_when_spinta_fails():
    from vitrina.statistics.services import build_dataset_stats

    dataset = DatasetFactory(published=datetime(2023, 5, 10, 10, 0, 0, tzinfo=timezone.utc))
    ModelFactory(dataset=dataset)
    DatasetStats.objects.create(created=dataset.published.date(), dataset_id=dataset.pk, object_count=999)

    with patch("vitrina.statistics.services.requests.get", side_effect=requests.RequestException):
        build_dataset_stats()

    stat = DatasetStats.objects.get(dataset_id=dataset.pk, created=dataset.published.date())
    assert stat.object_count == 999


@pytest.mark.django_db
def test_build_dataset_stats_preserves_object_count_when_response_has_no_data():
    from vitrina.statistics.services import build_dataset_stats

    dataset = DatasetFactory(published=datetime(2023, 5, 10, 10, 0, 0, tzinfo=timezone.utc))
    ModelFactory(dataset=dataset)
    DatasetStats.objects.create(created=dataset.published.date(), dataset_id=dataset.pk, object_count=999)

    response = Mock(content=json.dumps({"errors": ["not found"]}))
    with patch("vitrina.statistics.services.requests.get", return_value=response):
        build_dataset_stats()

    stat = DatasetStats.objects.get(dataset_id=dataset.pk, created=dataset.published.date())
    assert stat.object_count == 999


@pytest.mark.django_db
def test_build_dataset_stats_preserves_object_count_on_http_error():
    from vitrina.statistics.services import build_dataset_stats

    dataset = DatasetFactory(published=datetime(2023, 5, 10, 10, 0, 0, tzinfo=timezone.utc))
    ModelFactory(dataset=dataset)
    DatasetStats.objects.create(created=dataset.published.date(), dataset_id=dataset.pk, object_count=999)

    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    with patch("vitrina.statistics.services.requests.get", return_value=response):
        build_dataset_stats()

    stat = DatasetStats.objects.get(dataset_id=dataset.pk, created=dataset.published.date())
    assert stat.object_count == 999


@pytest.mark.django_db
def test_build_dataset_stats_counts_distributions_by_created_date():
    from vitrina.statistics.services import build_dataset_stats

    dataset = DatasetFactory(published=datetime(2023, 5, 10, 10, 0, 0, tzinfo=timezone.utc))
    distribution = DatasetDistributionFactory(dataset=dataset)
    build_dataset_stats()
    stat = DatasetStats.objects.get(dataset_id=dataset.pk, created=distribution.created.date())
    assert stat.distribution_count == 1


@pytest.mark.django_db
def test_create_dataset_stats_task_runs_the_service():
    from vitrina.statistics import tasks

    with patch.object(tasks, "build_dataset_stats") as service:
        tasks.create_dataset_stats()
    assert service.called


@pytest.mark.django_db
def test_create_dataset_stats_schedule_is_registered():
    from django_celery_beat.models import PeriodicTask

    assert PeriodicTask.objects.filter(task="vitrina.statistics.tasks.create_dataset_stats").exists()
