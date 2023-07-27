import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from tqdm import tqdm
from vitrina.datasets.models import DatasetStructure
from typer import run


def main():
    pbar = tqdm("Exporting dataset structure items", total=DatasetStructure.objects.count())

    total = 0
    total_not_csv = 0

    with pbar:
        for item in DatasetStructure.objects.all():
            if item.filename is not None:
                if 'csv' in item.filename:
                    total += 1
                    print(item.filename)
                else:
                    total_not_csv += 1

    print(f'Total CSV files found: {total}, other formats: {total_not_csv}')


if __name__ == '__main__':
    run(main)
