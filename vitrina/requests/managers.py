from django.db import models


class PublicRequestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
