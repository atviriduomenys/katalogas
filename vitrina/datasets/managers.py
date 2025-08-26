from django.db.models import Manager
from parler.managers import TranslatableManager, TranslatableQuerySet
from treebeard.mp_tree import MP_NodeQuerySet


class PublicDatasetManager(TranslatableManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                is_public=True,
                deleted__isnull=True,
                deleted_on__isnull=True,
                organization_id__isnull=False,
            )
        )

    def get_from_url_args(self, **kwargs):
        return self.get(id=kwargs.get("pk"))


class EdpPublicDatasetManager(TranslatableManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                access_rights=self.model.PUBLIC,
                deleted__isnull=True,
                deleted_on__isnull=True,
                organization_id__isnull=False,
            )
        )


class EdpRestrictedDatasetManager(TranslatableManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                access_rights=self.model.RESTRICTED,
                deleted__isnull=True,
                deleted_on__isnull=True,
                organization_id__isnull=False,
            )
        )


class TranslatableMPNodeQuerySet(TranslatableQuerySet, MP_NodeQuerySet):
    pass


class TranslatableMPNodeManager(Manager.from_queryset(TranslatableMPNodeQuerySet)):
    def get_queryset(self):
        return TranslatableMPNodeQuerySet(self.model).order_by("path")
