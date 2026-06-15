import itertools
import json
import logging

import requests
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F

from vitrina.datasets.models import Dataset
from vitrina.projects.models import Project
from vitrina.requests.models import RequestObject
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.statistics.models import DatasetStats
from vitrina.structure.models import Model, Property

logger = logging.getLogger(__name__)


def _update_stat_dict(stats, objects, stat_field):
    for obj in objects:
        if not obj["date"] or not obj["dataset_id"]:
            continue
        key = (obj["date"], obj["dataset_id"])
        if key in stats:
            stat_obj = stats[key]
        else:
            stat_obj, _ = DatasetStats.objects.get_or_create(created=obj["date"], dataset_id=obj["dataset_id"])
        setattr(stat_obj, stat_field, obj["count"])
        stats[key] = stat_obj
    return stats


def _get_distributions():
    return (
        DatasetDistribution.objects.annotate(date=F("created__date"))
        .values("date", "dataset_id")
        .annotate(count=Count("dataset"))
    )


def _get_projects():
    return (
        Project.objects.filter(datasets__pk__isnull=False)
        .annotate(date=F("created__date"), dataset_id=F("datasets__pk"))
        .values("date", "dataset_id")
        .annotate(count=Count("datasets"))
    )


def _get_requests():
    dataset_requests = list(
        RequestObject.objects.filter(content_type=ContentType.objects.get_for_model(Dataset))
        .annotate(date=F("request__created__date"), dataset_id=F("object_id"))
        .values("date", "dataset_id")
        .annotate(count=Count("object_id"))
    )

    dataset_property_requests = list(
        Property.objects.filter(requests__isnull=False)
        .annotate(date=F("requests__request__created__date"), dataset_id=F("model__dataset__pk"))
        .values("date", "dataset_id")
        .annotate(count=Count("requests"))
    )

    dataset_model_requests = list(
        Model.objects.filter(requests__isnull=False)
        .annotate(date=F("requests__request__created__date"))
        .values("date", "dataset_id")
        .annotate(count=Count("requests"))
    )

    dataset_requests.extend(dataset_model_requests)
    dataset_requests.extend(dataset_property_requests)
    dataset_requests = sorted(dataset_requests, key=lambda obj: (obj["date"], obj["dataset_id"]))

    dataset_requests_joined = []
    for (date, dataset_id), group in itertools.groupby(dataset_requests, lambda obj: (obj["date"], obj["dataset_id"])):
        dataset_requests_joined.append(
            {
                "date": date,
                "dataset_id": dataset_id,
                "count": sum([x["count"] for x in group]),
            }
        )
    return dataset_requests_joined


def _get_models():
    return Model.objects.annotate(date=F("created__date")).values("date", "dataset_id").annotate(count=Count("dataset"))


def _get_properties():
    return (
        Property.objects.annotate(date=F("created__date"), dataset_id=F("model__dataset__pk"))
        .values("date", "dataset_id")
        .annotate(count=Count("model__dataset"))
    )


def _fetch_object_count(model):
    """Return the object count for a model, or None if the Spinta request failed."""
    url = f"{SPINTA_SERVER_URL}/{model}?count()"
    try:
        response = requests.get(url, timeout=30)
        data = json.loads(response.content).get("_data", [])
    except (requests.RequestException, json.JSONDecodeError):
        logger.warning("Failed to retrieve object count for model: %s", model)
        return None
    if data:
        return data[0].get("count()", 0) or 0
    return 0


def _update_dataset_maturity_level_and_object_count_stats(stats, published_datasets):
    for dataset in published_datasets:
        object_count = 0
        fetch_failed = False
        for model in dataset.model_set.all():
            count = _fetch_object_count(str(model))
            if count is None:
                fetch_failed = True
            else:
                object_count += count
        maturity_level = dataset.get_level() or None

        key = (dataset.published.date(), dataset.pk)
        if key in stats:
            stat_obj = stats[key]
        else:
            stat_obj, _ = DatasetStats.objects.get_or_create(created=dataset.published.date(), dataset_id=dataset.pk)
        # don't overwrite a known object_count with a partial total when a
        # Spinta count() request failed for one of the dataset's models
        if not fetch_failed:
            stat_obj.object_count = object_count
        stat_obj.maturity_level = maturity_level
        stats[key] = stat_obj
    return stats


def build_dataset_stats():
    stats = {}

    published_datasets = Dataset.objects.filter(published__isnull=False)

    stats = _update_dataset_maturity_level_and_object_count_stats(stats, published_datasets)
    stats = _update_stat_dict(stats, _get_distributions(), "distribution_count")
    stats = _update_stat_dict(stats, _get_projects(), "project_count")
    stats = _update_stat_dict(stats, _get_requests(), "request_count")
    stats = _update_stat_dict(stats, _get_models(), "model_count")
    stats = _update_stat_dict(stats, _get_properties(), "field_count")

    DatasetStats.objects.bulk_update(
        stats.values(),
        fields=[
            "object_count",
            "field_count",
            "model_count",
            "distribution_count",
            "request_count",
            "project_count",
            "maturity_level",
        ],
    )
    logger.info("Updated dataset stats for %d (date, dataset) pairs", len(stats))
