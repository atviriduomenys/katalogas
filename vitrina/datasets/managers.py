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
        base_queryset: QuerySet["Dataset"] = (
            super()
            .get_queryset()
            .filter(
                deleted__isnull=True,
                deleted_on__isnull=True,
                organization_id__isnull=False,
            )
        )
        return self._filter_datasets_for_user(user, base_queryset)

    def _filter_datasets_for_user(self, user: "User", datasets: QuerySet["Dataset"]) -> QuerySet["Dataset"]:
        from vitrina.datasets.models import Dataset, Organization, Representative

        dataset_ct = ContentType.objects.get_for_model(Dataset)
        org_ct = ContentType.objects.get_for_model(Organization)

        accessible_filter: Q = Q(is_public=True, access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED))

        if not user.is_authenticated:
            return datasets.filter(accessible_filter)
        if user.is_staff or user.is_superuser:
            return datasets

        # Collect all dataset paths the user directly represents
        represented_dataset_paths = list(
            Dataset.objects.filter(
                pk__in=Representative.objects.filter(content_type=dataset_ct, user_id=user.id).values_list(
                    "object_id", flat=True
                )
            ).values_list("path", flat=True)
        )

        # Collect all organization paths the user directly represents
        represented_org_paths = list(
            Organization.objects.filter(
                pk__in=Representative.objects.filter(content_type=org_ct, user_id=user.id).values_list(
                    "object_id", flat=True
                )
            ).values_list("path", flat=True)
        )

        for ds_path in represented_dataset_paths:
            accessible_filter |= Q(path__startswith=ds_path)

        for org_path in represented_org_paths:
            accessible_filter |= Q(organization__path__startswith=org_path)

        if user.is_gov_organization_manager:
            accessible_filter |= Q(
                is_public=True,
                access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC),
            )

        return datasets.filter(accessible_filter).distinct()


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
