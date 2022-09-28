from django.db import models


class PublicDatasetManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(
            is_public=True,
            deleted__isnull=True,
            deleted_on__isnull=True,
            organization_id__isnull=False,
        )
