from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, get_object_or_404
from django.views import View

from vitrina.likes.models import Like
from vitrina.users.models import User


class LikeView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, obj_id, user_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        user = get_object_or_404(User, pk=user_id)
        Like.objects.create(
            content_type=content_type,
            object_id=obj.pk,
            user=user
        )
        return redirect(obj.get_absolute_url())


class UnlikeView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, obj_id, user_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        user = get_object_or_404(User, pk=user_id)
        if Like.objects.filter(content_type=content_type, object_id=obj.pk, user=user).exists():
            Like.objects.filter(content_type=content_type, object_id=obj.pk, user=user).delete()
        return redirect(obj.get_absolute_url())
