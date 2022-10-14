from enum import Enum
from typing import Type

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Representative, Organization
from vitrina.requests.models import Request
from vitrina.resources.models import DatasetDistribution
from vitrina.users.models import User


def has_coordinator_permission(user, organization):
    if user.is_authenticated:
        if user.is_staff:
            return True
        content_type = ContentType.objects.get_for_model(Organization)
        if user.representative_set.filter(object_id=organization.pk, content_type=content_type).exists():
            representative = (
                user.
                representative_set.
                filter(object_id=organization.pk, content_type=content_type).
                first()
            )
            return representative.role == Representative.COORDINATOR
    return False


class Action(Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'


def representative_exists(
        user: User,
        content_type: ContentType,
        object_id: int,
        role: str = None
) -> bool:
    representatives = Representative.objects.filter(
        user=user,
        object_id=object_id,
        content_type=content_type
    )
    if role:
        representatives = representatives.filter(role=role)
    return representatives.exists()


def has_perm(
    user: User,            # request.user
    action: Action,
    obj: (
        Model |            # when action is update, delete
        Type[Model]        # when action is create
    ),
    parent: Model | None = None,  # when action is create, object based on which a new objects is created
) -> bool:
    if user.is_authenticated:
        if user.is_staff or user.is_superuser:
            return True

        dataset_ct = ContentType.objects.get_for_model(Dataset)
        organization_ct = ContentType.objects.get_for_model(Organization)

        if action == Action.CREATE:
            if not parent:
                return False

            # if user is organization manager or coordinator, user can create dataset or request
            if (obj == Dataset or obj == Request) and isinstance(parent, Organization) \
                    and representative_exists(user, organization_ct, parent.pk):
                return True

            # if user is organization coordinator, user can create organization representative
            if obj == Representative and isinstance(parent, Organization) \
                    and representative_exists(user, organization_ct, parent.pk, Representative.COORDINATOR):
                return True

            # if user is dataset/request and dataset/request organization coordinator,
            # user can create dataset/request representative
            if obj == Representative and isinstance(parent, (Dataset, Request)):
                ct = ContentType.objects.get_for_model(parent)
                if representative_exists(user, ct, parent.pk, Representative.COORDINATOR) and \
                        representative_exists(user, organization_ct,
                                              parent.organization.pk, Representative.COORDINATOR):
                    return True
                # if user is only dataset/request coordinator, user can create dataset/request representative
                # only from organizations where user is coordinator
                elif representative_exists(user, ct, parent.pk, Representative.COORDINATOR):
                    # TODO: need to check if representative is from specific organization
                    # maybe this could go to form validation
                    pass

            # if user is dataset or dataset organization manager or coordinator, user can create dataset distribution
            if obj == DatasetDistribution and isinstance(parent, Dataset):
                if representative_exists(user, dataset_ct, parent.pk):
                    return True
                elif representative_exists(user, organization_ct, parent.organization.pk):
                    return True
        else:
            # if user is dataset/request or dataset/request organization manager or coordinator
            # user can manage dataset/request
            if isinstance(obj, (Dataset, Request)):
                ct = ContentType.objects.get_for_model(obj)
                if representative_exists(user, ct, obj.pk):
                    return True
                elif representative_exists(user, organization_ct, obj.organization.pk):
                    return True

            # if user is organization coordinator, user can manage organization
            if isinstance(obj, Organization) and \
                    representative_exists(user, organization_ct, obj.pk, Representative.COORDINATOR):
                return True

            # if user is organization representative, user can manage organization representative
            if isinstance(obj, Representative) and isinstance(obj.content_object, Organization) and \
                    representative_exists(user, organization_ct, obj.object_id, Representative.COORDINATOR):
                return True

            # if user is dataset/request and dataset/request organization coordinator,
            # user can manage dataset/request representative
            if isinstance(obj, Representative) and isinstance(obj.content_object, (Dataset, Request)):
                ct = ContentType.objects.get_for_model(obj.content_object)
                if representative_exists(user, ct, obj.object_id, Representative.COORDINATOR) and \
                    representative_exists(user, organization_ct,
                                          obj.content_object.organization.pk, Representative.COORDINATOR):
                    return True
                # if user is only dataset/request coordinator, user can manage dataset/request representative
                # if it is from organizations where user is coordinator
                elif representative_exists(user, ct, obj.object_id, Representative.COORDINATOR):
                    # TODO: need to check if representative is from specific organization
                    # if we don't remove organization attribute from representative, then need to check if
                    # obj.organization.pk in Representative.objects.filter(
                    #                         user=user,
                    #                         object_id=obj.object_id,
                    #                         content_type=organization_ct,
                    #                         role=Representative.COORDINATOR
                    #                 ).values_list('organization_id', flat=True)
                    pass

            # if user is dataset or dataset organization manager or coordinator, user can manage dataset distribution
            if isinstance(obj, DatasetDistribution):
                if representative_exists(user, dataset_ct, obj.dataset.pk):
                    return True
                if representative_exists(user, organization_ct, obj.dataset.organization.pk):
                    return True
    return False
