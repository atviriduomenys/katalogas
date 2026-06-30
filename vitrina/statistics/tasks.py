from celery import shared_task

from vitrina.statistics.services import build_dataset_stats


@shared_task
def create_dataset_stats():
    build_dataset_stats()
