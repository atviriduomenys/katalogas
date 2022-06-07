from django.db import models


class PublicProjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
