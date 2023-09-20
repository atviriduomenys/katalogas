import functools
import operator
from enum import Enum
from typing import Type

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.db.models import Q

from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.models import Representative, Organization
from vitrina.projects.models import Project
from vitrina.requests.models import Request
from vitrina.resources.models import DatasetDistribution
from vitrina.tasks.models import Task
from vitrina.users.models import User


class Action(Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    VIEW = 'view'
    HISTORY_VIEW = 'history_view'
    COMMENT = "comment_with_status"
    STRUCTURE = 'structure'
    PLAN = 'plan'


class Role(Enum):
    COORDINATOR = Representative.COORDINATOR
    MANAGER = Representative.MANAGER
    SUPERVISOR = Representative.SUPERVISOR
    AUTHOR = "author"
    ALL = "all"  # All authenticated users


acl = {
    (Organization, Action.UPDATE): [Role.COORDINATOR],
    (Organization, Action.PLAN): [Role.COORDINATOR, Role.MANAGER],
    (Organization, Action.HISTORY_VIEW): [Role.COORDINATOR, Role.MANAGER],
    (Representative, Action.CREATE): [Role.COORDINATOR],
    (Representative, Action.UPDATE): [Role.COORDINATOR],
    (Representative, Action.DELETE): [Role.COORDINATOR],
    (Representative, Action.VIEW): [Role.COORDINATOR],
    (Dataset, Action.CREATE): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.UPDATE): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.DELETE): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.HISTORY_VIEW): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.STRUCTURE): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.PLAN): [Role.COORDINATOR, Role.MANAGER],
    (Dataset, Action.VIEW): [Role.COORDINATOR],
    (DatasetDistribution, Action.CREATE): [Role.COORDINATOR, Role.MANAGER],
    (DatasetDistribution, Action.UPDATE): [Role.COORDINATOR, Role.MANAGER],
    (DatasetDistribution, Action.DELETE): [Role.COORDINATOR, Role.MANAGER],
    (DatasetStructure, Action.CREATE): [Role.COORDINATOR, Role.MANAGER],
    (Request, Action.CREATE): [Role.ALL],
    (Request, Action.UPDATE): [Role.AUTHOR, Role.SUPERVISOR],
    (Request, Action.DELETE): [Role.AUTHOR, Role.SUPERVISOR],
    (Request, Action.COMMENT): [Role.COORDINATOR, Role.MANAGER],
    (Request, Action.PLAN): [Role.AUTHOR, Role.SUPERVISOR],
    (Project, Action.CREATE): [Role.ALL],
    (Project, Action.UPDATE): [Role.AUTHOR],
    (Project, Action.DELETE): [Role.AUTHOR],
    (User, Action.UPDATE): [Role.AUTHOR],
    (User, Action.VIEW): [Role.AUTHOR],
    (Task, Action.UPDATE): [Role.ALL],

}


def is_author(user: User, node: Model) -> bool:
    if isinstance(node, (Dataset, Request, Project)):
        return node.user == user
    elif isinstance(node, User):
        return node == user
    elif isinstance(node, Organization):
        return False
    raise NotImplementedError(f"Don't know how to get author of {type(node)}.")


def is_supervisor(user: User, node: Model) -> bool:
    if isinstance(node, Organization):
        for rep in user.representative_set.all():
            if rep.is_supervisor(node):
                return True
    return False


def get_parents(obj: Model) -> list:
    return obj.get_acl_parents()


def has_perm(
    user: User,            # request.user
    action: Action,
    obj: (
        Model |            # when action is update, delete
        Type[Model]        # when action is create
    ),
    # when action is create, object based on which a new objects is created
    parent: Model | None = None,
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
                    elif role == Role.SUPERVISOR:
                        if is_supervisor(user, node):
                            return True
                    else:
                        ct = ContentType.objects.get_for_model(node)
                        where.append(Q(
                            content_type=ct,
                            object_id=node.pk,
                            role=role.value,
                        ))
    if where:
        where = functools.reduce(operator.or_, where)
        return Representative.objects.filter(where, user=user).exists()
    return False


def get_coordinators_count(model: Type[Model], object_id: int) -> int:
    ct = ContentType.objects.get_for_model(model)
    return (
        Representative.objects.
        filter(
            content_type=ct,
            object_id=object_id,
            role=Representative.COORDINATOR,
        ).
        count()
    )


def is_representative(user: User) -> bool:
    if user.is_authenticated:
        if user.is_staff or user.is_superuser:
            return True
        else:
            return Representative.objects.filter(
                user=user,
                content_type=ContentType.objects.get_for_model(Organization)
            ).exists()
    return False
