from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from vitrina.datasets.models import DatasetRelation


@receiver(post_save, sender=DatasetRelation)
def dataset_relation_post_save(**kwargs):
    instance = kwargs.get("instance")
    if instance:
        instance.dataset.save()
        instance.part_of.save()


@receiver(post_delete, sender=DatasetRelation)
def dataset_relation_post_delete(**kwargs):
    instance = kwargs.get("instance")
    if instance:
        instance.dataset.save()
        instance.part_of.save()
