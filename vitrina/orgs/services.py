import functools
import operator
from enum import Enum
from typing import Type

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q

from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.models import Representative, Organization
from vitrina.projects.models import Project
from vitrina.requests.models import Request
from vitrina.resources.models import DatasetDistribution
from vitrina.users.models import User


class Action(Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    VIEW = 'view'


class Role(Enum):
    COORDINATOR = Representative.COORDINATOR
    MANAGER = Representative.MANAGER
    AUTHOR = "author"
    ALL = "all"


acl = {
    (Organization, Action.UPDATE): [Role.COORDINATOR],
    (Representative, Action.CREATE): [Role.COORDINATOR],
    (Representative, Action.UPDATE): [Role.COORDINATOR],
    (Representative, Action.DELETE): [Role.COORDINATOR],
    (Representative, Action.VIEW): [Role.COORDINATOR],
    (Dataset, Action.CREATE): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.UPDATE): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.DELETE): [Role.COORDINATOR, Role.MANAGER],
    (DatasetDistribution, Action.CREATE): [Role.COORDINATOR, Role.MANAGER],
    (DatasetDistribution, Action.UPDATE): [Role.COORDINATOR, Role.MANAGER],
    (DatasetDistribution, Action.DELETE): [Role.COORDINATOR, Role.MANAGER],
    (DatasetStructure, Action.CREATE): [Role.COORDINATOR, Role.MANAGER],
    (Request, Action.CREATE): [Role.ALL],
    (Request, Action.UPDATE): [Role.AUTHOR],
    (Request, Action.DELETE): [Role.AUTHOR],
    (Project, Action.CREATE): [Role.ALL],
    (Project, Action.UPDATE): [Role.AUTHOR],
    (Project, Action.DELETE): [Role.AUTHOR],
    (User, Action.UPDATE): [Role.AUTHOR],
    (User, Action.VIEW): [Role.AUTHOR],
}


def is_author(user: User, node: Model) -> bool:
    if isinstance(node, (Dataset, Request, Project)):
        return node.user == user
    elif isinstance(node, User):
        return node == user
    raise NotImplementedError(f"Don't know how to get author of {type(node)}.")


def get_parents(obj: Model) -> list:
    return obj.get_acl_parents()


def has_perm(
    user: User,            # request.user
    action: Action,
    obj: (
        Model |            # when action is update, delete
        Type[Model]        # when action is create
    ),
    parent: Model | None = None,  # when action is create, object based on which a new objects is created
) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    if isinstance(obj, Type):
        model = obj
        if parent:
            nodes = get_parents(parent)
        else:
            nodes = []
    else:
        model = type(obj)
        nodes = get_parents(obj)

    where = []
    if acl.get((model, action)):
        for role in acl[(model, action)]:
            if role == Role.ALL:
                return True
            else:
                for node in nodes:
                    if role == Role.AUTHOR:
                        if is_author(user, node):
                            return True
                    else:
                        ct = ContentType.objects.get_for_model(node)
                        where.append(Q(content_type=ct, object_id=node.pk, role=role.value))
    if where:
        where = functools.reduce(operator.or_, where)
        return Representative.objects.filter(where, user=user).exists()
    return False
