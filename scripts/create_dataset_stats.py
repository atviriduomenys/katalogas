import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from typer import run

from vitrina.statistics.services import build_dataset_stats


def main():
    build_dataset_stats()


if __name__ == "__main__":
    run(main)
