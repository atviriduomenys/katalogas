import functools
import inspect
import operator
from enum import Enum
from typing import Type, cast, Union

from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

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
from vitrina.structure.models import Metadata, Model, Property, Enum as StructureEnum
from vitrina.tasks.models import Task
from vitrina.uapi.models import Agent, AgentEnvironment
from vitrina.users.models import User


class Action(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REQUEST_UPDATE = "request_update"
    INFORMATION_SYSTEM_UPDATE = "information_system_update"
    INFORMATION_SYSTEM_REPRESENTATIVE_CREATE = "information_system_representative_create"
    VIEW = "view"
    HISTORY_VIEW = "history_view"
    COMMENT = "comment_with_status"
    STRUCTURE = "structure"
    PLAN = "plan"
    MANAGE_KEYS = "manage_keys"
    MANAGE_PROJECT_KEYS = "manage_project_keys"
    ASSIGN = "assign"


class Role(Enum):
    RESOURCE_COORDINATOR = Representative.RESOURCE_COORDINATOR
    RESOURCE_MANAGER = Representative.RESOURCE_MANAGER
    OPEN_DATA_COORDINATOR = Representative.OPEN_DATA_COORDINATOR
    OPEN_DATA_MANAGER = Representative.OPEN_DATA_MANAGER
    GLOBAL_RESOURCE_MANAGER = "global_resource_manager"  # All resource managers
    SUPERVISOR = Representative.SUPERVISOR
    AUTHOR = "author"
    GLOBAL_MANAGER = "global_manager"  # Global Manager (is staff)
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
    Action.INFORMATION_SYSTEM_UPDATE,
    Action.INFORMATION_SYSTEM_REPRESENTATIVE_CREATE,
}
DATASET_RELATED_OBJECTS: set[Type[Model]] = {
    Dataset,
    DatasetDistribution,
    DatasetStructure,
    DatasetAttribution,
    DatasetRelation,
    Request,
}
EXCLUDED_ACTIONS: set[Action] = {
    Action.CREATE,
    Action.ASSIGN,
    Action.PLAN,
    Action.REQUEST_UPDATE,
    Action.INFORMATION_SYSTEM_REPRESENTATIVE_CREATE,
}

DATASET_IS_PUBLIC = True
ACL_RULE = tuple[type[Model], Action]
EXISTING_DATASET_ACL_RULE = tuple[
    Union[Dataset, DatasetDistribution, DatasetStructure, DatasetRelation, Request], bool, str, Action
]
ACL = dict[ACL_RULE | EXISTING_DATASET_ACL_RULE, set[Role] | tuple[Role]]


def inherit_acl(
    base_acl: ACL,
    new_model_class: type[Model] | None = None,
    new_action: Action | None = None,
    new_roles: set[Role] | None = None,
) -> ACL:
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
        new_acl[new_rule] = new_roles or roles
    return new_acl


def inherit_structure_acl(
    base_acl: ACL,
    new_model_class: Property | StructureEnum,
) -> ACL:
    new_acl = {}
    for (cls, visibility, action), roles in base_acl.items():
        new_acl[(new_model_class, visibility, action)] = roles.copy()
    return new_acl


_dataset_update_acl: ACL = {
    (Dataset, DATASET_IS_PUBLIC, Dataset.PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    },
    (Dataset, DATASET_IS_PUBLIC, Dataset.RESTRICTED, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    },
    (Dataset, DATASET_IS_PUBLIC, Dataset.NON_PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, DATASET_IS_PUBLIC, Dataset.CONFIDENTIAL, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, not DATASET_IS_PUBLIC, Dataset.PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    },
    (Dataset, not DATASET_IS_PUBLIC, Dataset.RESTRICTED, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    },
    (Dataset, not DATASET_IS_PUBLIC, Dataset.NON_PUBLIC, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
    (Dataset, not DATASET_IS_PUBLIC, Dataset.CONFIDENTIAL, Action.UPDATE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
}
_dataset_view_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.VIEW) | {
    (Dataset, DATASET_IS_PUBLIC, Dataset.PUBLIC, Action.VIEW): {
        Role.AUTHENTICATED,
        Role.VISITOR,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.GLOBAL_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
        Role.GLOBAL_RESOURCE_MANAGER,
    },
    (Dataset, DATASET_IS_PUBLIC, Dataset.RESTRICTED, Action.VIEW): {
        Role.AUTHENTICATED,
        Role.VISITOR,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.GLOBAL_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
        Role.GLOBAL_RESOURCE_MANAGER,
    },
    (Dataset, DATASET_IS_PUBLIC, Dataset.NON_PUBLIC, Action.VIEW): {
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.GLOBAL_MANAGER,
        Role.GLOBAL_RESOURCE_MANAGER,
    },
}

_dataset_create_acl: ACL = {
    (Dataset, Action.CREATE): (
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.GLOBAL_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    )
}
_information_system_update_acl: ACL = inherit_acl(
    _dataset_update_acl,
    new_action=Action.INFORMATION_SYSTEM_UPDATE,
    new_roles={Role.RESOURCE_COORDINATOR, Role.GLOBAL_MANAGER, Role.RESOURCE_MANAGER},
)

_dataset_comment_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.COMMENT)
_dataset_delete_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.DELETE)
_dataset_history_view_acl: ACL = inherit_acl(_dataset_view_acl, new_action=Action.HISTORY_VIEW)
_dataset_structure_acl: ACL = inherit_acl(_dataset_update_acl, new_action=Action.STRUCTURE) | inherit_acl(
    _dataset_view_acl,
    new_model_class=DatasetStructure,
    new_action=Action.STRUCTURE,
)

_dataset_distribution_create_acl: ACL = inherit_acl(_dataset_create_acl, new_model_class=DatasetDistribution)
_dataset_distribution_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetDistribution)
_dataset_distribution_delete_acl: ACL = inherit_acl(_dataset_delete_acl, new_model_class=DatasetDistribution)

_dataset_attribution_create_acl: ACL = inherit_acl(_dataset_create_acl, new_model_class=DatasetAttribution)
_dataset_attribution_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetAttribution)
_dataset_attribution_delete_acl: ACL = inherit_acl(_dataset_delete_acl, new_model_class=DatasetAttribution)

_dataset_relation_create_acl: ACL = inherit_acl(_dataset_create_acl, new_model_class=DatasetRelation)
_dataset_relation_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=DatasetRelation)
_dataset_relation_delete_acl: ACL = inherit_acl(
    _dataset_delete_acl,
    new_model_class=DatasetRelation,
)

_dataset_request_create_acl: ACL = inherit_acl(_dataset_create_acl, new_model_class=Request)
_dataset_request_update_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Request)
_dataset_request_delete_acl: ACL = inherit_acl(_dataset_delete_acl, new_model_class=Request, new_action=Action.DELETE)
_dataset_request_comment_acl: ACL = inherit_acl(_dataset_update_acl, new_model_class=Request, new_action=Action.COMMENT)
_dataset_request_history_view_acl: ACL = inherit_acl(
    _dataset_history_view_acl, new_model_class=Request, new_roles={Role.GLOBAL_MANAGER}
)
_dataset_structure_create_acl: ACL = inherit_acl(_dataset_create_acl, new_model_class=DatasetStructure)

MODEL_VISIBILITY_ACL = {
    (Model, Metadata.UNDEFINED, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
        Role.GLOBAL_RESOURCE_MANAGER,
        Role.AUTHENTICATED,
        Role.VISITOR,
    },
    (Model, Metadata.VISIBILITY_PUBLIC, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
        Role.GLOBAL_RESOURCE_MANAGER,
        Role.AUTHENTICATED,
        Role.VISITOR,
    },
    (Model, Metadata.PACKAGE, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
        Role.GLOBAL_RESOURCE_MANAGER,
        Role.AUTHENTICATED,
        Role.VISITOR,
    },
    (Model, Metadata.PROTECTED, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
    (Model, Metadata.PRIVATE, Action.VIEW): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
    (Model, Metadata.UNDEFINED, Action.STRUCTURE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    },
    (Model, Metadata.VISIBILITY_PUBLIC, Action.STRUCTURE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    },
    (Model, Metadata.PACKAGE, Action.STRUCTURE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
        Role.OPEN_DATA_COORDINATOR,
        Role.OPEN_DATA_MANAGER,
    },
    (Model, Metadata.PROTECTED, Action.STRUCTURE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
    (Model, Metadata.PRIVATE, Action.STRUCTURE): {
        Role.GLOBAL_MANAGER,
        Role.RESOURCE_COORDINATOR,
        Role.RESOURCE_MANAGER,
    },
}
PROPERTY_VISIBILITY_ACL = inherit_structure_acl(MODEL_VISIBILITY_ACL, Property)
ENUM_VISIBILITY_ACL = inherit_structure_acl(MODEL_VISIBILITY_ACL, StructureEnum)


acl: ACL = (
    _dataset_view_acl
    | _dataset_create_acl
    | _information_system_update_acl
    | _dataset_update_acl
    | _dataset_comment_acl
    | _dataset_delete_acl
    | _dataset_history_view_acl
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
    | _dataset_request_comment_acl
    | _dataset_request_history_view_acl
    | _dataset_structure_acl
    | _dataset_structure_create_acl
    | {
        (Organization, Action.UPDATE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR),
        (Organization, Action.PLAN): (
            Role.RESOURCE_COORDINATOR,
            Role.RESOURCE_MANAGER,
            Role.OPEN_DATA_COORDINATOR,
            Role.OPEN_DATA_MANAGER,
        ),
        (Organization, Action.HISTORY_VIEW): (
            Role.RESOURCE_COORDINATOR,
            Role.RESOURCE_MANAGER,
            Role.OPEN_DATA_COORDINATOR,
            Role.OPEN_DATA_MANAGER,
        ),
        (Agent, Action.CREATE): (Role.RESOURCE_COORDINATOR,),
        (Agent, Action.VIEW): (Role.RESOURCE_COORDINATOR,),
        (Agent, Action.UPDATE): (Role.RESOURCE_COORDINATOR,),
        (Agent, Action.DELETE): (Role.RESOURCE_COORDINATOR,),
        (AgentEnvironment, Action.CREATE): (Role.RESOURCE_COORDINATOR,),
        (AgentEnvironment, Action.VIEW): (Role.RESOURCE_COORDINATOR,),
        (AgentEnvironment, Action.UPDATE): (Role.RESOURCE_COORDINATOR,),
        (AgentEnvironment, Action.DELETE): (Role.RESOURCE_COORDINATOR,),
        (Agreement, Action.CREATE): (Role.AUTHOR,),
        (Agreement, Action.VIEW): (Role.AUTHOR,),
        (Contact, Action.CREATE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR),
        (Contact, Action.UPDATE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR),
        (Contact, Action.DELETE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR),
        (Contact, Action.VIEW): (
            Role.RESOURCE_COORDINATOR,
            Role.RESOURCE_MANAGER,
            Role.OPEN_DATA_COORDINATOR,
            Role.OPEN_DATA_MANAGER,
        ),
        (Request, Action.CREATE): (Role.AUTHENTICATED,),
        (Request, Action.REQUEST_UPDATE): (Role.AUTHOR,),
        (Request, Action.DELETE): (Role.AUTHOR,),
        (Request, Action.COMMENT): (
            Role.RESOURCE_COORDINATOR,
            Role.RESOURCE_MANAGER,
            Role.OPEN_DATA_COORDINATOR,
            Role.OPEN_DATA_MANAGER,
        ),
        (Request, Action.VIEW): (
            Role.AUTHOR,
            Role.RESOURCE_COORDINATOR,
            Role.RESOURCE_MANAGER,
            Role.OPEN_DATA_COORDINATOR,
            Role.OPEN_DATA_MANAGER,
        ),
        (Request, Action.PLAN): (
            Role.RESOURCE_COORDINATOR,
            Role.RESOURCE_MANAGER,
            Role.OPEN_DATA_COORDINATOR,
            Role.OPEN_DATA_MANAGER,
        ),
        (Request, Action.ASSIGN): (
            Role.RESOURCE_COORDINATOR,
            Role.RESOURCE_MANAGER,
            Role.OPEN_DATA_COORDINATOR,
            Role.OPEN_DATA_MANAGER,
        ),
        (Project, Action.CREATE): (Role.AUTHENTICATED,),
        (Project, Action.UPDATE): (Role.AUTHOR,),
        (Project, Action.DELETE): (Role.AUTHOR,),
        (Project, Action.VIEW): (Role.AUTHOR,),
        (User, Action.UPDATE): (Role.AUTHOR,),
        (User, Action.VIEW): (Role.AUTHOR,),
        (Task, Action.UPDATE): (Role.AUTHENTICATED,),
        (Organization, Action.MANAGE_KEYS): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR),
        (Project, Action.MANAGE_PROJECT_KEYS): (Role.AUTHOR, Role.SUPERVISOR),
        (RequestAssignment, Action.CREATE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR),
        (RequestAssignment, Action.DELETE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR),
        (ApiExample, Action.CREATE): (Role.RESOURCE_COORDINATOR, Role.RESOURCE_MANAGER),
        (Representative, Action.CREATE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR, Role.GLOBAL_MANAGER),
        (Representative, Action.INFORMATION_SYSTEM_REPRESENTATIVE_CREATE): (
            Role.RESOURCE_COORDINATOR,
            Role.GLOBAL_MANAGER,
        ),
        (Representative, Action.UPDATE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR, Role.GLOBAL_MANAGER),
        (Representative, Action.DELETE): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR, Role.GLOBAL_MANAGER),
        (Representative, Action.VIEW): (Role.RESOURCE_COORDINATOR, Role.OPEN_DATA_COORDINATOR, Role.GLOBAL_MANAGER),
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
    if (
        resource.get_managers_queryset(
            [
                Representative.RESOURCE_COORDINATOR,
                Representative.RESOURCE_MANAGER,
            ]
        )
        .filter(user=user)
        .exists()
    ):
        return Role.RESOURCE_COORDINATOR if user.is_resource_coordinator else Role.RESOURCE_MANAGER

    if (
        resource.get_managers_queryset(
            [
                Representative.OPEN_DATA_COORDINATOR,
                Representative.OPEN_DATA_MANAGER,
            ]
        )
        .filter(user=user)
        .exists()
    ):
        return Role.OPEN_DATA_COORDINATOR if user.is_open_data_coordinator else Role.OPEN_DATA_MANAGER
    if user.is_gov_organization_resource_manager:
        return Role.GLOBAL_RESOURCE_MANAGER
    return Role.AUTHENTICATED


def _get_dataset_instance(obj: Model) -> Dataset | None:
    if isinstance(obj, Dataset):
        dataset = obj
    elif hasattr(obj, "dataset"):
        dataset = getattr(obj, "dataset")
    elif hasattr(obj, "content_type") and hasattr(obj, "object_id"):
        content_object = getattr(obj, "content_object")
        if isinstance(content_object, Dataset):
            dataset = content_object
        else:
            dataset = None
    else:
        raise NotImplementedError(f"Dataset field does not exist on {obj=}")

    return dataset


def _has_dataset_perm(user: User, action: Action, obj: Model, dataset: Dataset) -> bool:
    for current_dataset in [dataset, *dataset.get_ancestors()]:
        rule: EXISTING_DATASET_ACL_RULE = (
            obj.__class__,
            current_dataset.is_public,
            current_dataset.access_rights,
            action,
        )
        user_role: Role = determine_user_role(user, current_dataset)
        allowed_roles = acl.get(rule)
        has_perm: bool = allowed_roles and user_role in allowed_roles
        if has_perm and action in WRITE_ACTIONS:
            return True

        if has_perm and current_dataset == dataset:
            return True

    return False


def has_perm(
    user: User,  # request.user
    action: Action,
    obj: Model | Type[Model],  # when action is update, delete
    parent: Model | None = None,  # when action is create, object based on which new object is created
) -> bool:
    if user.is_authenticated and user.is_superuser:
        return True
    if parent:
        class_object = parent.__class__
    elif inspect.isclass(obj):
        class_object = obj
    else:
        class_object = obj.__class__
    if (
        action not in EXCLUDED_ACTIONS
        and class_object in DATASET_RELATED_OBJECTS
        and (dataset := _get_dataset_instance(parent or obj))
    ):
        return _has_dataset_perm(user, action, parent or obj, dataset)
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
        roles = acl.get((model, action))
        if not roles:
            return False
        user_org = getattr(user, "organization", None)
        for role in roles:
            if role == Role.AUTHENTICATED:
                return True
            for node in nodes:
                if (role == Role.AUTHOR and is_author(user, node)) or (
                    role == Role.SUPERVISOR and is_supervisor(user, node)
                ):
                    return True
                if role not in {Role.AUTHOR, Role.SUPERVISOR}:
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
                if isinstance(obj, Representative):
                    return obj.can_be_updated_by(user)
                return True

            if user_org and Representative.objects.filter(where, organization=user_org).exists():
                if isinstance(obj, Representative):
                    return obj.can_be_updated_by(user)

                user_viisp_org = getattr(user, "viisp_organization", None)

                if model == Organization and action == Action.UPDATE:
                    return user_viisp_org == obj

                if model == Representative and action == Action.UPDATE and parent and isinstance(parent, Organization):
                    return user_viisp_org == parent
                return True

        return False


def get_coordinators_count(model: Type[Model], object_id: int) -> int:
    ct = ContentType.objects.get_for_model(model)
    return Representative.objects.filter(
        content_type=ct,
        object_id=object_id,
        role__in=Representative.COORDINATOR_ROLES,
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
