from django.contrib.contenttypes.models import ContentType
from django.db.models import Manager, QuerySet, Q
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


class PermittedDatasetManager(TranslatableManager):
    def for_user(self, user: "User") -> QuerySet["Dataset"]:
        base_qs: QuerySet["Dataset"] = (
            super()
            .get_queryset()
            .filter(
                deleted__isnull=True,
                deleted_on__isnull=True,
                organization_id__isnull=False,
            )
        )
        return self._filter_datasets_for_user(user, base_qs)

    def _filter_datasets_for_user(self, user: "User", datasets: QuerySet["Dataset"]) -> QuerySet["Dataset"]:
        from vitrina.datasets.models import Dataset, Organization, Representative

        public_filter: Q = Q(is_public=True, access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED))

        if not user.is_authenticated:
            return datasets.filter(public_filter)
        if user.is_staff or user.is_superuser:
            return datasets
        if user.is_gov_organization_manager:
            return datasets.filter(
                Q(is_public=True, access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC))
            )

        dataset_ct = ContentType.objects.get_for_model(Dataset)
        org_ct = ContentType.objects.get_for_model(Organization)

        user_dataset_ids = set(
            Representative.objects.filter(content_type=dataset_ct, user_id=user.id).values_list("object_id", flat=True)
        )

        user_org_ids = set(
            Representative.objects.filter(content_type=org_ct, user_id=user.id).values_list("object_id", flat=True)
        )

        accessible_ids = set()
        for ds in datasets:
            ds_and_ancestors = [ds.pk] + [d.pk for d in ds.get_ancestors()]
            if user_dataset_ids.intersection(ds_and_ancestors):
                accessible_ids.add(ds.pk)
                continue

            if ds.organization and ds.organization.pk in user_org_ids:
                accessible_ids.add(ds.pk)
                continue

        return datasets.filter(Q(pk__in=accessible_ids) | public_filter)


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
