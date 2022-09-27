from django.db import models


class PublicDatasetManager(models.Manager):
    def get_queryset(self):
        all_datasets = super().get_queryset()
        public_datasets = all_datasets.filter(is_public__isnull=False).filter(is_public=True)
        not_deleted_public_datasets = public_datasets.filter(deleted__isnull=True, deleted_on__isnull=True)
        datasets_with_orgs = not_deleted_public_datasets.filter(organization_id__isnull=False)
        return datasets_with_orgs
