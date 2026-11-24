from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from vitrina.datasets.models import DatasetRelation, Dataset
from vitrina.search.signals import index_dataset_on_save


@receiver(post_save, sender=DatasetRelation)
def dataset_relation_post_save(**kwargs):
    instance = kwargs.get("instance")
    if instance:
        index_dataset_on_save(Dataset, instance.dataset)
        index_dataset_on_save(Dataset, instance.part_of)


@receiver(post_delete, sender=DatasetRelation)
def dataset_relation_post_delete(**kwargs):
    instance = kwargs.get("instance")
    if instance:
        index_dataset_on_save(Dataset, instance.dataset)
        index_dataset_on_save(Dataset, instance.part_of)
