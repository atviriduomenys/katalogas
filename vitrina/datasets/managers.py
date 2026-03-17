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
        from vitrina.datasets.models import Dataset, Organization, Representative

        dataset_ct = ContentType.objects.get_for_model(Dataset)
        org_ct = ContentType.objects.get_for_model(Organization)

        accessible_filter: Q = Q(is_public=True, access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED))

        if not user.is_authenticated:
            return datasets.filter(accessible_filter)
        if user.is_staff or user.is_superuser:
            return datasets

        user_org_ids = list(
            Representative.objects.filter(
                user=user,
                content_type=org_ct,
            ).values_list("object_id", flat=True)
        )

        if user.organization:
            user_org_ids.append(user.organization.pk)

        resource_roles = (Representative.RESOURCE_MANAGER, Representative.RESOURCE_COORDINATOR)
        resource_representatives = Representative.objects.filter(user_id=user.id, role__in=resource_roles)

        represented_dataset_ids = resource_representatives.filter(content_type=dataset_ct).values_list(
            "object_id", flat=True
        )
        represented_org_ids = resource_representatives.filter(content_type=org_ct).values_list("object_id", flat=True)

        # Organizations that represent datasets with resource roles, that the user belongs to
        org_represented_dataset_ids = Representative.objects.filter(
            content_type=dataset_ct,
            role__in=resource_roles,
            organization__in=user_org_ids,
        ).values_list("object_id", flat=True)

        # Organizations that represent other organizations with resource roles, that the user belongs to
        org_represented_org_ids = Representative.objects.filter(
            content_type=org_ct,
            role__in=resource_roles,
            organization__in=user_org_ids,
        ).values_list("object_id", flat=True)

        represented_paths = set(
            Dataset.objects.filter(
                Q(pk__in=represented_dataset_ids)
                | Q(organization_id__in=represented_org_ids)
                | Q(pk__in=org_represented_dataset_ids)
                | Q(organization_id__in=org_represented_org_ids)
            ).values_list("path", flat=True)
        )

        for path in represented_paths:
            accessible_filter |= Q(path__startswith=path)

        open_data_roles = (Representative.OPEN_DATA_MANAGER, Representative.OPEN_DATA_COORDINATOR)
        open_data_representatives = Representative.objects.filter(user_id=user.id, role__in=open_data_roles)

        open_data_dataset_ids = open_data_representatives.filter(content_type=dataset_ct).values_list(
            "object_id", flat=True
        )
        open_data_org_ids = open_data_representatives.filter(content_type=org_ct).values_list("object_id", flat=True)

        org_represented_open_data_dataset_ids = Representative.objects.filter(
            content_type=dataset_ct,
            role__in=open_data_roles,
            organization__in=user_org_ids,
        ).values_list("object_id", flat=True)

        org_represented_open_data_org_ids = Representative.objects.filter(
            content_type=org_ct,
            role__in=open_data_roles,
            organization__in=user_org_ids,
        ).values_list("object_id", flat=True)

        open_data_paths = set(
            Dataset.objects.filter(
                Q(pk__in=open_data_dataset_ids)
                | Q(organization_id__in=open_data_org_ids)
                | Q(pk__in=org_represented_open_data_dataset_ids)
                | Q(organization_id__in=org_represented_open_data_org_ids)
            ).values_list("path", flat=True)
        )

        for path in open_data_paths:
            accessible_filter |= Q(path__startswith=path, access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED))

        if user.is_gov_organization_resource_manager:
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
