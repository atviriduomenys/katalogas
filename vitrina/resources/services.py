from django.shortcuts import get_object_or_404

from vitrina.datasets.models import Dataset
from vitrina.resources.models import DatasetDistribution
from vitrina.users.models import User


def permission_checker(user, dataset):
    permission = False
    if user.is_authenticated:
        if user.organization_id:
            if user.organization_id == dataset.organization_id:
                permission = True
        if user.is_staff or dataset.manager == user:
            permission = True
    return permission


def can_add_resource(user: User, dataset_pk) -> bool:
    dataset = get_object_or_404(Dataset, id=dataset_pk)
    return permission_checker(user, dataset)


def can_change_resource(user: User, resource_pk):
    resource = get_object_or_404(DatasetDistribution, id=resource_pk)
    return permission_checker(user, resource.dataset)
