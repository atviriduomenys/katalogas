from typing import Type

from django.db import models

from vitrina.comments.forms import DatasetCommentForm, RequestCommentForm, CommentForm, ProjectCommentForm, \
    RegisterRequestForm
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.requests.models import Request
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import Property, Model
from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks
from vitrina.users.models import User


def get_comment_form_class(obj: models.Model = None, user: User = None) -> Type:
    if isinstance(obj, Dataset):
        return DatasetCommentForm
    elif isinstance(obj, Request) and has_perm(user, Action.COMMENT, obj):
        return RequestCommentForm
    elif isinstance(obj, Project) and has_perm(user, Action.COMMENT, obj):
        return ProjectCommentForm
    elif isinstance(obj, (Property, Model)) or obj is None:
        return RegisterRequestForm
    return CommentForm


def has_comment_permission(obj: models.Model = None, user: User = None) -> bool:
    if isinstance(obj, (Dataset, Model, Property, DatasetStructure, DatasetDistribution)):
        if isinstance(obj, (Model, DatasetStructure, DatasetDistribution)):
            dataset = obj.dataset
        elif isinstance(obj, Property):
            dataset = obj.model.dataset
        else:
            dataset = obj
        if dataset and hasattr(dataset, 'is_public') and dataset.is_public:
            return True
        else:
            return has_perm(user, Action.VIEW, dataset)
    elif isinstance(obj, Task):
        user_tasks = get_active_tasks(user, all_tasks=True)
        if user_tasks.filter(pk=obj.pk):
            return True
    elif isinstance(obj, (Request, Project)):
        return True
    return False
