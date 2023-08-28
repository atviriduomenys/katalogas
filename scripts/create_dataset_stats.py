import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import json
import requests
from tqdm import tqdm
from typer import run

from django.contrib.contenttypes.models import ContentType
from vitrina.datasets.models import Dataset
from vitrina.statistics.models import DatasetStats
from vitrina.structure.models import Property
from vitrina.requests.models import RequestObject


def main():
    pbar = tqdm("Creating dataset stats", total=Dataset.objects.count())

    for dataset in Dataset.objects.all():
        object_count = 0
        for model in dataset.model_set.all():
            res = requests.get(f"https://get.data.gov.lt/{str(model)}?count()")
            data = json.loads(res.content)
            data = data.get('_data', [])
            if data:
                count = data[0].get('count()', 0)
                object_count += count

        model_count = dataset.model_set.count()
        field_count = Property.objects.filter(
            model__dataset=dataset,
            given=True
        ).count()
        distribution_count = dataset.datasetdistribution_set.count()
        request_count = RequestObject.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id=dataset.pk
        ).count()
        project_count = dataset.project_set.count()
        maturity_level = dataset.get_level() or 0

        DatasetStats.objects.create(
            dataset_id=dataset.pk,
            object_count=object_count,
            field_count=field_count,
            model_count=model_count,
            distribution_count=distribution_count,
            request_count=request_count,
            project_count=project_count,
            maturity_level=maturity_level
        )
        pbar.update(1)


if __name__ == '__main__':
    run(main)
