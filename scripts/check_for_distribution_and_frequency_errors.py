import math
import os
import django
import pandas as pd
import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from tqdm import tqdm
from django.contrib.contenttypes.models import ContentType
from vitrina.orgs.models import Organization
from vitrina.resources.models import DatasetDistribution
from vitrina.datasets.models import Dataset
from vitrina.tasks.models import Task
from typer import run
from datetime import datetime, timezone
from time import sleep


def main():
    pbar = tqdm('Checking for external distributions', total=DatasetDistribution.objects.count())

    total_distributions = 0
    total_unavailable = 0
    frequency_entries = 0
    frequency_mismatch = 0
    tasks_created = 0
    tasks_closed = 0

    with (pbar):
        for item in DatasetDistribution.objects.all()[0:25]:
            if item.is_external_url():
                task = Task.objects.filter(content_type=ContentType.objects.get_for_model(item.dataset),
                                           object_id=item.dataset.pk,
                                           type=Task.ERROR_DISTRIBUTION).first()
                url = item.download_url
                try:
                    request_response = requests.head(url)
                    status_code = request_response.status_code
                    website_is_up = status_code == 200
                    if not website_is_up:
                        print('Distribution url is down:', url)
                        if not task:
                            print(f'Task for {item.dataset.pk} does not exist, creating...')
                            create_task_for_dataset(
                                item.dataset.pk,
                                f'Klaida duomenų rinkinio id: {item.dataset.pk} duomenų šaltinyje',
                                f'Duomenų rinkinio šaltinio nuoroda {url} yra neveikianti.',
                                Task.ERROR_DISTRIBUTION
                            )
                            tasks_created += 1
                        total_unavailable += 1
                    elif website_is_up:
                        if task:
                            close_task(task)
                            tasks_closed += 1
                    total_distributions += 1
                    pbar.update(1)
                    sleep(1.5)
                except:
                    print(f'Error retrieving url: {url}')

    pbar2 = tqdm('Checking update frequencies', total=Dataset.objects.count())
    with (pbar2):
        for dt in Dataset.objects.all():
            if dt.frequency is not None:
                now = datetime.now(timezone.utc)
                last_update = pd.to_datetime(dt.modified)
                diff = abs(math.trunc((last_update - now).total_seconds() / 60 / 60))
                task = Task.objects.filter(content_type=ContentType.objects.get_for_model(dt),
                                           object_id=dt.pk,
                                           type=Task.ERROR_FREQUENCY).first()
                if dt.frequency.hours < diff:
                    if not task:
                        print(f'Task for {dt.pk} does not exist, creating...')
                        create_task_for_dataset(
                            dt.pk,
                            f'Klaida duomenų rinkinio id: {dt.pk} atnaujinimo intervale',
                            f'Duomenų rinkinys neatnaujintas pagal numatytą atnaujinimo dažnumą.\n'
                            f'Numatytas atnaujinimo dažnumas kas {dt.frequency.hours} valandas,'
                            f' paskutinį kartą atnaujintas prieš {diff} valandas.',
                            Task.ERROR_FREQUENCY
                        )
                        tasks_created += 1
                    frequency_mismatch += 1
                elif dt.frequency.hours > diff:
                    if task:
                        close_task(task)
                        tasks_closed += 1
                frequency_entries += 1
            pbar2.update(1)

    print(f'Total external resources found: {total_distributions}.\n'
          f'Failed to fetch distributions: {total_unavailable}.\n'
          f'Total update frequencies: {frequency_entries}.\n'
          f'Total errors in update frequency: {frequency_mismatch}.\n'
          f'Total tasks created: {tasks_created}.\n'
          f'Total tasks closed: {tasks_closed}.')


def create_task_for_dataset(dataset_id, title, desc, error_type):
    target_dataset = Dataset.objects.get(pk=dataset_id)
    org = Organization.objects.get(pk=target_dataset.organization.pk)
    Task.objects.create(
        content_type=ContentType.objects.get_for_model(target_dataset),
        object_id=target_dataset.pk,
        organization=org,
        title=title,
        status=Task.CREATED,
        type=error_type,
        description=desc
    )


def close_task(task):
    task.status = Task.COMPLETED
    task.completed = datetime.now(timezone.utc)
    task.save()


if __name__ == '__main__':
    run(main)
