from parler.managers import TranslatableManager


class PublicDatasetManager(TranslatableManager):

    def get_queryset(self):
        return super().get_queryset().filter(
            is_public=True,
            deleted__isnull=True,
            deleted_on__isnull=True,
            organization_id__isnull=False,
        )
