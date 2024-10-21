from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.shortcuts import redirect, get_object_or_404
from django.views import View

from vitrina.datasets.models import Dataset
from vitrina.likes.models import Like
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.users.models import User


class LikeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    content_type: ContentType
    obj: Model
    user: User

    def dispatch(self, request, *args, **kwargs):
        self.content_type = get_object_or_404(ContentType, pk=kwargs.get('content_type_id'))
        self.obj = get_object_or_404(self.content_type.model_class(), pk=kwargs.get('obj_id'))
        self.user = get_object_or_404(User, pk=kwargs.get('user_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if isinstance(self.obj, Dataset):
            if self.obj.is_public:
                return True
            else:
                return has_perm(self.request.user, Action.VIEW, self.obj)
        elif isinstance(self.obj, Project):
            if self.obj.status == Project.APPROVED or self.obj.user == self.request.user:
                return True
            else:
                return has_perm(
                    self.request.user,
                    Action.UPDATE,
                    self.obj,
                )
        return True

    def post(self, request, *args, **kwargs):
        Like.objects.create(
            content_type=self.content_type,
            object_id=self.obj.pk,
            user=self.user
        )
        return redirect(self.obj.get_absolute_url())


class UnlikeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    content_type: ContentType
    obj: Model
    user: User

    def dispatch(self, request, *args, **kwargs):
        self.content_type = get_object_or_404(ContentType, pk=kwargs.get('content_type_id'))
        self.obj = get_object_or_404(self.content_type.model_class(), pk=kwargs.get('obj_id'))
        self.user = get_object_or_404(User, pk=kwargs.get('user_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if isinstance(self.obj, Dataset):
            if self.obj.is_public:
                return True
            else:
                return has_perm(self.request.user, Action.VIEW, self.obj)
        elif isinstance(self.obj, Project):
            if self.obj.status == Project.APPROVED or self.obj.user == self.request.user:
                return True
            else:
                return has_perm(
                    self.request.user,
                    Action.UPDATE,
                    self.obj,
                )
        return True

    def post(self, request, *args, **kwargs):
        if Like.objects.filter(content_type=self.content_type, object_id=self.obj.pk, user=self.user).exists():
            Like.objects.filter(content_type=self.content_type, object_id=self.obj.pk, user=self.user).delete()
        return redirect(self.obj.get_absolute_url())
