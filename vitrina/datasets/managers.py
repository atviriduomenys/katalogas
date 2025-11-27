from typing import TYPE_CHECKING

from django.contrib.contenttypes.models import ContentType
from django.db.models import Manager, QuerySet, Q
from parler.managers import TranslatableManager, TranslatableQuerySet
from treebeard.mp_tree import MP_NodeQuerySet

if TYPE_CHECKING:
    from vitrina.datasets.models import Dataset
    from vitrina.users.models import User


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
        from vitrina.datasets.models import Dataset, Organization, Representative, DCATResourceSubclass

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

        represented_orgs = Organization.objects.filter(
            pk__in=Representative.objects.filter(
                content_type=org_ct,
                user_id=user.id,
                information_system_representative=False,
                open_data_representative=False,
            ).values_list("object_id", flat=True)
        )

        datasets_in_represented_orgs = Dataset.objects.filter(organization__in=represented_orgs)
        represented_dataset_paths += list(datasets_in_represented_orgs.values_list("path", flat=True))

        for ds_path in represented_dataset_paths:
            accessible_filter |= Q(path__startswith=ds_path)

        info_system_orgs = Representative.objects.filter(
            content_type=org_ct, user_id=user.id, information_system_representative=True
        ).values_list("object_id", flat=True)

        if info_system_orgs.all():
            accessible_filter |= Q(
                organization__in=info_system_orgs,
                subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM,
                is_public=True,
                access_rights__in=(
                    Dataset.PUBLIC,
                    Dataset.RESTRICTED,
                    Dataset.NON_PUBLIC,
                    Dataset.CONFIDENTIAL,
                ),
            )
            accessible_filter |= Q(
                organization__in=info_system_orgs,
                is_public=True,
                access_rights__in=(
                    Dataset.PUBLIC,
                    Dataset.RESTRICTED,
                    Dataset.NON_PUBLIC,
                ),
            ) & ~Q(subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM)

        open_data_orgs = Representative.objects.filter(
            content_type=org_ct, user_id=user.id, open_data_representative=True
        ).values_list("object_id", flat=True)

        if open_data_orgs.exists():
            accessible_filter |= Q(
                organization__in=open_data_orgs,
                is_public=True,
                access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED),
            )

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
