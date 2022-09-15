from django.db import models
from django.db.models import Q


class PublicDatasetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(~Q(is_public=False))
