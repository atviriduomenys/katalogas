import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import itertools
import json
import requests
from tqdm import tqdm
from typer import run
from django.db.models import Count, F
from django.contrib.contenttypes.models import ContentType
from vitrina.datasets.models import Dataset
from vitrina.statistics.models import DatasetStats
from vitrina.structure.models import Property, Model
from vitrina.requests.models import RequestObject
from vitrina.projects.models import Project
from vitrina.resources.models import DatasetDistribution


def _update_stat_dict(
    stats,
    objects,
    stat_field,
    pbar
):
    for obj in objects:
        key = (obj['date'], obj['dataset_id'])
        if key in stats:
            stat_obj = stats[key]
        else:
            stat_obj, _ = DatasetStats.objects.get_or_create(
                created=obj['date'],
                dataset_id=obj['dataset_id']
            )
        setattr(stat_obj, stat_field, obj['count'])
        stats[key] = stat_obj
        pbar.update(1)
    return stats


def _get_distributions():
    return DatasetDistribution.objects.annotate(
        date=F('created__date')
    ).values(
        'date',
        'dataset_id'
    ).annotate(count=Count('dataset'))


def _get_projects():
    return Project.objects.filter(
        datasets__pk__isnull=False
    ).annotate(
        date=F('created__date'),
        dataset_id=F('datasets__pk')
    ).values(
        'date',
        'dataset_id'
    ).annotate(count=Count('datasets'))


def _get_requests():
    dataset_requests = list(RequestObject.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset)
    ).annotate(
        date=F('request__created__date'),
        dataset_id=F('object_id')
    ).values(
        'date',
        'dataset_id'
    ).annotate(count=Count('object_id')))

    dataset_property_requests = list(Property.objects.filter(
        requests__isnull=False
    ).annotate(
        date=F('requests__request__created__date'),
        dataset_id=F('model__dataset__pk')
    ).values(
        'date',
        'dataset_id'
    ).annotate(count=Count('requests')))

    dataset_model_requests = list(Model.objects.filter(
        requests__isnull=False
    ).annotate(
        date=F('requests__request__created__date'),
    ).values(
        'date',
        'dataset_id'
    ).annotate(count=Count('requests')))

    dataset_requests.extend(dataset_model_requests)
    dataset_requests.extend(dataset_property_requests)
    dataset_requests = sorted(dataset_requests, key=lambda obj: (obj['date'], obj['dataset_id']))

    dataset_requests_joined = []
    for (date, dataset_id), group in itertools.groupby(
            dataset_requests,
            lambda obj: (obj['date'], obj['dataset_id'])
    ):
        dataset_requests_joined.append({
            'date': date,
            'dataset_id': dataset_id,
            'count': sum([x['count'] for x in group])
        })
    return dataset_requests_joined


def _get_models():
    return Model.objects.annotate(
        date=F('created__date')
    ).values(
        'date',
        'dataset_id'
    ).annotate(count=Count('dataset'))


def _get_properties():
    return Property.objects.annotate(
        date=F('created__date'),
        dataset_id=F('model__dataset__pk')
    ).values(
        'date',
        'dataset_id'
    ).annotate(count=Count('model__dataset'))


def _update_dataset_maturity_level_and_object_count_stats(
    stats,
    published_datasets,
    pbar
):
    for dataset in published_datasets:
        object_count = 0
        for model in dataset.model_set.all():
            res = requests.get(f"https://get.data.gov.lt/{str(model)}?count()")
            data = json.loads(res.content)
            data = data.get('_data', [])
            if data:
                count = data[0].get('count()', 0)
                object_count += count
        maturity_level = dataset.get_level() or None

        key = (dataset.published.date(), dataset.pk)
        if key in stats:
            stat_obj = stats[key]
        else:
            stat_obj, _ = DatasetStats.objects.get_or_create(
                created=dataset.published.date(),
                dataset_id=dataset.pk
            )
        stat_obj.object_count = object_count
        stat_obj.maturity_level = maturity_level
        stats[key] = stat_obj
        pbar.update(1)
    return stats


def main():
    stats = {}

    published_datasets = Dataset.objects.filter(published__isnull=False)
    dataset_distributions = _get_distributions()
    dataset_projects = _get_projects()
    dataset_requests = _get_requests()
    dataset_models = _get_models()
    dataset_properties = _get_properties()

    pbar = tqdm("Creating dataset stats", total=(
        len(published_datasets) +
        len(dataset_distributions) +
        len(dataset_projects) +
        len(dataset_requests) +
        len(dataset_models) +
        len(dataset_properties)
    ))

    # Dataset maturity level and object count stats
    stats = _update_dataset_maturity_level_and_object_count_stats(
        stats,
        published_datasets,
        pbar
    )

    # Dataset distribution stats
    stats = _update_stat_dict(
        stats,
        dataset_distributions,
        'distribution_count',
        pbar
    )

    # Dataset project stats
    stats = _update_stat_dict(
        stats,
        dataset_projects,
        'project_count',
        pbar
    )

    # Dataset request stats
    stats = _update_stat_dict(
        stats,
        dataset_requests,
        'request_count',
        pbar
    )

    # Dataset model stats
    stats = _update_stat_dict(
        stats,
        dataset_models,
        'model_count',
        pbar
    )

    # Dataset property stats
    stats = _update_stat_dict(
        stats,
        dataset_properties,
        'field_count',
        pbar
    )

    DatasetStats.objects.bulk_update(stats.values(), fields=[
        'object_count',
        'field_count',
        'model_count',
        'distribution_count',
        'request_count',
        'project_count',
        'maturity_level'
    ])


if __name__ == '__main__':
    run(main)
