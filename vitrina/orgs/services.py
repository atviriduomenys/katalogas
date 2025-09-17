import functools
import inspect
import operator
from enum import Enum
from typing import Type, cast, Union

from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q

from vitrina import settings
from vitrina.api_example.models import ApiExample
from vitrina.datasets.models import (
    Dataset,
    DatasetStructure,
    Contact,
    DatasetAttribution,
    DatasetRelation,
)
from vitrina.helpers import email
from vitrina.messages.models import Subscription
from vitrina.orgs.models import Representative, Organization
from vitrina.projects.models import Project
from vitrina.requests.models import Request, RequestAssignment
from vitrina.resources.models import DatasetDistribution
from vitrina.smart_contracts.models import Agreement
from vitrina.tasks.models import Task
from vitrina.uapi.models import Agent
from vitrina.users.models import User


class Action(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    HISTORY_VIEW = "history_view"
    COMMENT = "comment_with_status"
    STRUCTURE = "structure"
    PLAN = "plan"
    MANAGE_KEYS = "manage_keys"
    MANAGE_PROJECT_KEYS = "manage_project_keys"
    ASSIGN = "assign"


class Role(Enum):
    COORDINATOR = Representative.COORDINATOR
    MANAGER = Representative.MANAGER  # Visi Tvarkytojai
    RESOURCE_MANAGER = "resource_manager"  # Ištekliaus Tvarkytojas
    GLOBAL_MANAGER = "global_manager"  # Globalus Tvarkytojas (is staff)
    SUPERVISOR = Representative.SUPERVISOR
    AUTHOR = "author"
    AUTHENTICATED = "all"  # All authenticated users
    VISITOR = "visitor"  # All unauthenticated users


WRITE_ACTIONS: set[Action] = {
    Action.CREATE,
    Action.UPDATE,
    Action.DELETE,
    Action.COMMENT,
    Action.STRUCTURE,
    Action.PLAN,
    Action.MANAGE_KEYS,
    Action.MANAGE_PROJECT_KEYS,
    Action.ASSIGN,
}
DATASET_RELATED_OBJECTS: set[Type[Model]] = {
    Dataset,
    DatasetDistribution,
    DatasetStructure,
    DatasetAttribution,
    DatasetRelation,
    Request,
    Representative,
    # TODO check these
    # Project,
    # Plan,
    # Contact,
    # PlanDataset,
    # Metadata,
    # Model,
    # Version,
}
IS_PUBLIC_DATASET = True
ACL_RULE = tuple[type[Model], Action]
EXISTING_DATASET_ACL_RULE = tuple[Union[DATASET_RELATED_OBJECTS], bool, str, Action]
ACL = dict[ACL_RULE | EXISTING_DATASET_ACL_RULE, set[Role] | tuple[Role]]


def inherit_acl(base_acl: ACL, new_model_class: type[Model] | None = None, new_action: Action | None = None) -> ACL:
    action_position_in_rule = -1
    model_class_position_in_rule = 0
    new_acl = {}
    for rule, roles in base_acl.items():
        new_rule = list(rule)
        if new_action:
            new_rule[action_position_in_rule] = new_action
        if new_model_class:
            new_rule[model_class_position_in_rule] = new_model_class
        new_rule = cast(ACL_RULE, tuple(new_rule))
        new_acl[new_rule] = roles
    return new_acl


_dataset_update_acl: ACL = {
    (Dataset, IS_PUBLIC_DATASET, Dataset.PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, IS_PUBLIC_DATASET, Dataset.RESTRICTED, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, IS_PUBLIC_DATASET, Dataset.NON_PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, IS_PUBLIC_DATASET, Dataset.CONFIDENTIAL, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,  # TODO additional logic
    },
    (Dataset, not IS_PUBLIC_DATASET, Dataset.PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, not IS_PUBLIC_DATASET, Dataset.RESTRICTED, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, not IS_PUBLIC_DATASET, Dataset.NON_PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, not IS_PUBLIC_DATASET, Dataset.CONFIDENTIAL, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
    },
}
_dataset_view_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.VIEW) | {
    (Dataset, IS_PUBLIC_DATASET, Dataset.PUBLIC, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
        Role.MANAGER,
        Role.AUTHENTICATED,
        Role.VISITOR,
    },
    (Dataset, IS_PUBLIC_DATASET, Dataset.RESTRICTED, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
        Role.MANAGER,
        Role.AUTHENTICATED,
        Role.VISITOR,
    },
    (Dataset, IS_PUBLIC_DATASET, Dataset.NON_PUBLIC, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_MANAGER,
        Role.MANAGER,
    },
}

_dataset_create_acl: ACL = {(Dataset, Action.CREATE): (Role.COORDINATOR, Role.MANAGER, Role.GLOBAL_MANAGER)}

_dataset_comment_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.COMMENT)
_dataset_delete_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.DELETE)
_dataset_history_view_acl: ACL = inherit_acl(_dataset_view_acl, new_action=Action.HISTORY_VIEW)
_dataset_structure_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.STRUCTURE) | inherit_acl(
    _dataset_view_acl, new_model_class=DatasetStructure, new_action=Action.STRUCTURE
)
_dataset_plan_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.PLAN)

_dataset_distribution_create_acl: ACL = inherit_acl(_dataset_create_acl, new_model_class=DatasetDistribution)
_dataset_distribution_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetDistribution)
_dataset_distribution_delete_acl: ACL = inherit_acl(_dataset_delete_acl, new_model_class=DatasetDistribution)

_dataset_attribution_create_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetAttribution)
_dataset_attribution_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetAttribution)
_dataset_attribution_delete_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetAttribution)

_dataset_relation_create_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetRelation)
_dataset_relation_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetRelation)
_dataset_relation_delete_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetRelation)

_dataset_request_create_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Request)
_dataset_request_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Request)
_dataset_request_delete_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Request)

_dataset_representative_create_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Representative)
_dataset_representative_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Representative)
_dataset_representative_delete_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Representative)

_dataset_structure_create_acl: ACL = inherit_acl(
    _dataset_create_acl, new_model_class=DatasetStructure, new_action=Action.STRUCTURE
)


acl: ACL = (
    _dataset_view_acl
    | _dataset_create_acl
    | _dataset_update_acl
    | _dataset_comment_acl
    | _dataset_delete_acl
    | _dataset_history_view_acl
    | _dataset_plan_acl
    | _dataset_distribution_create_acl
    | _dataset_distribution_update_acl
    | _dataset_distribution_delete_acl
    | _dataset_attribution_create_acl
    | _dataset_attribution_update_acl
    | _dataset_attribution_delete_acl
    | _dataset_relation_create_acl
    | _dataset_relation_update_acl
    | _dataset_relation_delete_acl
    | _dataset_request_create_acl
    | _dataset_request_update_acl
    | _dataset_request_delete_acl
    | _dataset_representative_create_acl
    | _dataset_representative_update_acl
    | _dataset_representative_delete_acl
    | _dataset_structure_acl
    | _dataset_structure_create_acl
    | {
        (Organization, Action.UPDATE): (Role.COORDINATOR,),
        (Organization, Action.PLAN): (Role.COORDINATOR, Role.MANAGER),
        (Organization, Action.HISTORY_VIEW): (Role.COORDINATOR, Role.MANAGER),
        (Representative, Action.CREATE): (Role.COORDINATOR,),
        (Representative, Action.UPDATE): (Role.COORDINATOR,),
        (Representative, Action.DELETE): (Role.COORDINATOR,),
        (Representative, Action.VIEW): (Role.COORDINATOR,),
        (Agent, Action.CREATE): (Role.COORDINATOR, Role.MANAGER),
        (Agent, Action.VIEW): (Role.COORDINATOR, Role.MANAGER),
        (Agent, Action.UPDATE): (Role.COORDINATOR, Role.MANAGER),
        (Agent, Action.DELETE): (Role.COORDINATOR, Role.MANAGER),
        (Agreement, Action.CREATE): (Role.AUTHOR,),
        (Agreement, Action.VIEW): (Role.AUTHOR,),
        (Contact, Action.CREATE): (Role.COORDINATOR,),
        (Contact, Action.UPDATE): (Role.COORDINATOR,),
        (Contact, Action.DELETE): (Role.COORDINATOR,),
        (Contact, Action.VIEW): (Role.COORDINATOR, Role.MANAGER),
        (Request, Action.CREATE): (Role.AUTHENTICATED,),
        (Request, Action.UPDATE): (Role.AUTHOR,),
        (Request, Action.DELETE): (Role.AUTHOR,),
        (Request, Action.COMMENT): (Role.COORDINATOR, Role.MANAGER),
        (Request, Action.VIEW): (Role.AUTHOR, Role.COORDINATOR, Role.MANAGER),
        (Request, Action.PLAN): (Role.COORDINATOR, Role.MANAGER),
        (Request, Action.ASSIGN): (Role.COORDINATOR, Role.MANAGER),
        (Project, Action.CREATE): (Role.AUTHENTICATED,),
        (Project, Action.UPDATE): (Role.AUTHOR,),
        (Project, Action.DELETE): (Role.AUTHOR,),
        (Project, Action.VIEW): (Role.AUTHOR,),
        (User, Action.UPDATE): (Role.AUTHOR,),
        (User, Action.VIEW): (Role.AUTHOR,),
        (Task, Action.UPDATE): (Role.AUTHENTICATED,),
        (Organization, Action.MANAGE_KEYS): (Role.COORDINATOR, Role.MANAGER),
        (Project, Action.MANAGE_PROJECT_KEYS): (Role.AUTHOR, Role.SUPERVISOR),
        (RequestAssignment, Action.CREATE): (Role.COORDINATOR,),
        (RequestAssignment, Action.DELETE): (Role.COORDINATOR,),
        (ApiExample, Action.CREATE): (Role.COORDINATOR, Role.MANAGER),
    }
)


def is_author(user: User, node: Model) -> bool:
    if isinstance(node, (Dataset, Request, Project)):
        return node.user == user
    elif isinstance(node, User):
        return node == user
    elif isinstance(node, Organization):
        return False
    elif isinstance(node, Agreement):
        return node.project.user == user
    raise NotImplementedError(f"Don't know how to get author of {type(node)}.")


def is_supervisor(user: User, node: Model) -> bool:
    if isinstance(node, Organization):
        for rep in user.representative_set.all():
            if rep.is_supervisor(node):
                return True
    return False


def is_manager(user: User, node: Model) -> bool:
    if isinstance(node, Organization):
        for rep in user.representative_set.all():
            if rep.role == "manager":
                return True
    return False


def get_parents(obj: Model) -> list:
    return obj.get_acl_parents()


def determine_user_role(user: User, resource: Dataset) -> Role:
    if not user.is_authenticated:
        return Role.VISITOR
    if user.is_staff:
        return Role.GLOBAL_MANAGER
    if user.is_gov_organization_manager:
        return Role.MANAGER
    if resource.get_resource_managers_queryset().filter(user=user).exists():
        return Role.RESOURCE_MANAGER
    return Role.AUTHENTICATED


def _get_dataset_instance(obj: Model) -> Dataset:
    if isinstance(obj, Dataset):
        dataset = obj
    elif hasattr(obj, "dataset"):
        dataset = getattr(obj, "dataset")
    elif hasattr(obj, "content_type") and hasattr(obj, "object_id"):
        content_object = getattr(obj, "content_object")
        if isinstance(content_object, Dataset):
            dataset = content_object
        else:
            raise Dataset.DoesNotExist(f"Cannot determine dataset from {obj}")
    else:
        raise NotImplementedError(f"Dataset field does not exist on {obj=}")

    return dataset


def _has_dataset_perm(user: User, action: Action, obj: Model) -> bool:
    dataset: Dataset = _get_dataset_instance(obj)

    rule: EXISTING_DATASET_ACL_RULE = obj.__class__, dataset.is_public, dataset.access_rights, action
    user_role: Role = determine_user_role(user, dataset)
    allowed_roles = acl[rule]
    has_perm: bool = allowed_roles and user_role in allowed_roles
    is_confidential_dataset = dataset.access_rights == dataset.CONFIDENTIAL
    if has_perm and action in WRITE_ACTIONS and is_confidential_dataset:
        return Representative.objects.filter(
            Q(content_type=ContentType.objects.get_for_model(Dataset), object_id=dataset.pk)
            | Q(content_type=ContentType.objects.get_for_model(Organization), object_id=dataset.organization.pk),
            user=user,
            can_write=True,
        ).exists()

    return has_perm


def has_perm(
    user: User,  # request.user
    action: Action,
    obj: Model | Type[Model],  # when action is update, delete
    parent: Model | None = None,  # when action is create, object based on which new object is created
) -> bool:
    if user.is_authenticated and user.is_superuser:
        return True
    if parent:
        klass = parent.__class__
    elif inspect.isclass(obj):
        klass = obj
    else:
        klass = obj.__class__
    if action != Action.CREATE and klass in DATASET_RELATED_OBJECTS:
        return _has_dataset_perm(user, action, parent or obj)
    else:
        if not user.is_authenticated:
            return False

        if user.is_staff:
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
                if role == Role.AUTHENTICATED:
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
                            where.append(
                                Q(
                                    content_type=ct,
                                    object_id=node.pk,
                                    role=role.value,
                                )
                            )
        if where:
            where = functools.reduce(operator.or_, where)
            if Representative.objects.filter(where, user=user).exists():
                return True

            user_org = getattr(user, "organization", None)
            if user_org and Representative.objects.filter(where, organization=user_org).exists():
                return True
        return False


def get_coordinators_count(model: Type[Model], object_id: int) -> int:
    ct = ContentType.objects.get_for_model(model)
    return Representative.objects.filter(
        content_type=ct,
        object_id=object_id,
        role=Representative.COORDINATOR,
    ).count()


def hash_api_key(api_key: str) -> str:
    hasher = PBKDF2PasswordHasher()
    salt = settings.HASHER_SALT
    return hasher.encode(api_key, salt)


def create_subscription(user, organization):
    return Subscription.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=organization.pk,
        sub_type=Subscription.ORGANIZATION,
        email_subscribed=True,
        dataset_comments_sub=True,
        request_comments_sub=True,
        project_comments_sub=True,
        request_update_sub=True,
    )


def manage_subscriptions_for_representative(subscribe, user, organization, link):
    subscription = Subscription.objects.filter(
        user=user,
        object_id=organization.id,
        content_type=get_content_type_for_model(Organization),
    )
    if subscribe:
        if not subscription:
            create_subscription(user, organization)
            if user.email:
                email(
                    [user.email],
                    "newsletter-org-subscription-created-representative",
                    "vitrina/orgs/emails/subscribed.md",
                    {"organization": organization, "link": link},
                )
        else:
            subscription.update(
                dataset_comments_sub=True,
                request_comments_sub=True,
                project_comments_sub=True,
            )
            email(
                [user.email],
                "newsletter-org-subscription-updated-representative",
                "vitrina/orgs/emails/subscription_updated.md",
                {"organization": organization, "link": link},
            )
    else:
        if subscription:
            subscription.delete()


def pre_representative_delete(rep: Representative):
    if isinstance(rep.content_object, Organization) and rep.user:
        org_repr = rep.user.representative_set.filter(content_type=ContentType.objects.get_for_model(Organization))
        dataset_repr_object_ids = rep.user.representative_set.filter(
            content_type=ContentType.objects.get_for_model(Dataset)
        ).values_list("object_id", flat=True)

        if org_repr.count() == 1 and not Dataset.objects.filter(id__in=dataset_repr_object_ids).exclude(
            organization_id=rep.object_id
        ):
            rep.user.is_active = False
            rep.user.status = User.SUSPENDED
            rep.user.save()
