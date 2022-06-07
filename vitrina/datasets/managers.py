from django.db import models


class PublicDatasetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
