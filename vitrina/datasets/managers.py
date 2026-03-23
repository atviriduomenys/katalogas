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

        dataset_content_type = ContentType.objects.get_for_model(Dataset)
        organization_content_type = ContentType.objects.get_for_model(Organization)

        # Default filter grants access only to publicly available datasets.
        accessible_filter: Q = Q(is_public=True, access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED))

        if not user.is_authenticated:
            return datasets.filter(accessible_filter)
        if user.is_staff or user.is_superuser:
            return datasets

        resource_roles = (Representative.RESOURCE_MANAGER, Representative.RESOURCE_COORDINATOR)
        open_data_roles = (Representative.OPEN_DATA_MANAGER, Representative.OPEN_DATA_COORDINATOR)

        # Partition the user's organizational memberships by role level.
        # The user's own role serves as an upper bound when resolving access through the organization chain.
        resource_level_user_organization_ids = list(
            Representative.objects.filter(
                user=user,
                content_type=organization_content_type,
                role__in=resource_roles,
            )
            .exclude(deleted=True)
            .values_list("object_id", flat=True)
        )
        open_data_level_user_organization_ids = list(
            Representative.objects.filter(
                user=user,
                content_type=organization_content_type,
                role__in=open_data_roles,
            )
            .exclude(deleted=True)
            .values_list("object_id", flat=True)
        )

        if user.organization:
            resource_level_user_organization_ids.append(user.organization.pk)

        # Datasets and organizations the user directly represents with a resource-level role.
        direct_resource_representatives = Representative.objects.filter(user_id=user.id, role__in=resource_roles)
        direct_resource_dataset_ids = direct_resource_representatives.filter(
            content_type=dataset_content_type
        ).values_list("object_id", flat=True)
        direct_resource_organization_ids = direct_resource_representatives.filter(
            content_type=organization_content_type
        ).values_list("object_id", flat=True)

        # Resolve access through organizations where the user holds a resource-level role.
        # Full resource access is granted when the represented entity also holds a resource-level role.
        organization_chain_resource_dataset_ids = Representative.objects.filter(
            content_type=dataset_content_type,
            role__in=resource_roles,
            organization__in=resource_level_user_organization_ids,
        ).values_list("object_id", flat=True)

        organization_chain_resource_organization_ids = Representative.objects.filter(
            content_type=organization_content_type,
            role__in=resource_roles,
            organization__in=resource_level_user_organization_ids,
        ).values_list("object_id", flat=True)

        resource_accessible_paths = set(
            Dataset.objects.filter(
                Q(pk__in=direct_resource_dataset_ids)
                | Q(organization_id__in=direct_resource_organization_ids)
                | Q(pk__in=organization_chain_resource_dataset_ids)
                | Q(organization_id__in=organization_chain_resource_organization_ids)
            ).values_list("path", flat=True)
        )

        for path in resource_accessible_paths:
            accessible_filter |= Q(path__startswith=path)

        # Datasets and organizations the user directly represents with an open data role.
        direct_open_data_representatives = Representative.objects.filter(user_id=user.id, role__in=open_data_roles)
        direct_open_data_dataset_ids = direct_open_data_representatives.filter(
            content_type=dataset_content_type
        ).values_list("object_id", flat=True)
        direct_open_data_organization_ids = direct_open_data_representatives.filter(
            content_type=organization_content_type
        ).values_list("object_id", flat=True)

        # Resolve access through organizations where the user holds a resource-level role,
        # but the represented entity holds an open data role.
        # Effective access is restricted to open data level as it is the least privileged of the two roles.
        resource_user_organization_chain_open_data_dataset_ids = Representative.objects.filter(
            content_type=dataset_content_type,
            role__in=open_data_roles,
            organization__in=resource_level_user_organization_ids,
        ).values_list("object_id", flat=True)

        resource_user_organization_chain_open_data_organization_ids = Representative.objects.filter(
            content_type=organization_content_type,
            role__in=open_data_roles,
            organization__in=resource_level_user_organization_ids,
        ).values_list("object_id", flat=True)

        # Resolve access through organizations where the user holds an open data role.
        # Access is always restricted to open data level regardless of the represented entity's role.
        open_data_user_organization_chain_dataset_ids = Representative.objects.filter(
            content_type=dataset_content_type,
            organization__in=open_data_level_user_organization_ids,
        ).values_list("object_id", flat=True)

        open_data_user_organization_chain_organization_ids = Representative.objects.filter(
            content_type=organization_content_type,
            organization__in=open_data_level_user_organization_ids,
        ).values_list("object_id", flat=True)

        open_data_accessible_paths = set(
            Dataset.objects.filter(
                Q(pk__in=direct_open_data_dataset_ids)
                | Q(organization_id__in=direct_open_data_organization_ids)
                | Q(pk__in=open_data_user_organization_chain_dataset_ids)
                | Q(organization_id__in=open_data_user_organization_chain_organization_ids)
                | Q(pk__in=resource_user_organization_chain_open_data_dataset_ids)
                | Q(organization_id__in=resource_user_organization_chain_open_data_organization_ids)
            ).values_list("path", flat=True)
        )

        for path in open_data_accessible_paths:
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
