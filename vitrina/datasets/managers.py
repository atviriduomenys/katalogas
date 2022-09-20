from django.db import models


class PublicDatasetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()

    def get_from_url_args(self, **kwargs):
        return self.get(id=kwargs.get('pk'))
