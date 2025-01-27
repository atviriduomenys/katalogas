import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from typer import run
from tqdm import tqdm
from vitrina.datasets.models import Dataset


def main():
    """
    Remove Geoportal datasets
    """

    datasets = Dataset.objects.filter(geoportal_id__isnull=False)
    pbar = tqdm("Removing Geoportal datasets", total=len(datasets))

    for dataset in datasets:
        dataset.tasks.all().delete()
        dataset.delete()
        pbar.update(1)


if __name__ == '__main__':
    run(main)
