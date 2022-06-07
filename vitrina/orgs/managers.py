from django.db import models


class PublicOrganizationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
