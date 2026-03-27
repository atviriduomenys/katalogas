from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet

from vitrina.datasets.models import Dataset
from vitrina.datasets.services import filter_out_non_public_datasets_for_user
from vitrina.orgs.models import Representative
from haystack.query import SearchQuerySet


class DatasetAccessMixin:
    def is_open_data_representative(self) -> bool:
        if self.user:
            return self.user.is_open_data_representative_for(self.organization)
        if self.organization_role:
            return self.organization_role in Representative.OPEN_DATA_ROLE_KEYS
        return False

    def _filter_queryset_by_access(self, queryset: QuerySet[Dataset]) -> QuerySet[Dataset]:
        if not self.user and not self.organization_role:
            return Dataset.objects.none()

        if self.user:
            search_queryset = (
                SearchQuerySet().models(Dataset).filter(django_id__in=queryset.values_list("id", flat=True))
            )
            datasets = filter_out_non_public_datasets_for_user(self.user, search_queryset)
            ids = datasets.models(Dataset).values_list("pk", flat=True)
            return queryset.filter(pk__in=ids)
        elif self.organization_role:
            if self.organization_role in Representative.OPEN_DATA_ROLE_KEYS:
                return queryset.filter(access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED))
            else:
                return queryset

    def _check_dataset_access(self, dataset: Dataset) -> None:
        if self.user:
            search_queryset = SearchQuerySet().models(Dataset).filter(django_id=dataset.id)
            if not filter_out_non_public_datasets_for_user(self.user, search_queryset):
                raise PermissionDenied()
        elif self.organization and self.organization_role:
            if self.organization_role in Representative.OPEN_DATA_ROLE_KEYS and dataset.access_rights not in (
                Dataset.PUBLIC,
                Dataset.RESTRICTED,
            ):
                raise PermissionDenied()
        else:
            raise PermissionDenied()

    def _is_restricted_information_system(self, dataset: Dataset) -> bool:
        return self.is_open_data_representative() and dataset.subclass.is_information_system
