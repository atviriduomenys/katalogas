from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.comments.forms import CommentForm
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class
from vitrina.requests.models import Request


class CommentView(
    LoginRequiredMixin,
    RevisionMixin,
    View
):
    def post(self, request, content_type_id, object_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=object_id)
        form_class = get_comment_form_class(obj, request.user)
        form = form_class(obj, request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.content_type = content_type
            comment.object_id = object_id

            if form.cleaned_data.get('register_request'):
                frequency = form.cleaned_data.get('increase_frequency')
                new_request = Request.objects.create(
                    status=Request.CREATED,
                    user=request.user,
                    title=obj.title,
                    description=comment.body,
                    organization=obj.organization,
                    dataset_id=object_id,
                    periodicity=frequency.title if frequency else "",
                )
                set_comment(Request.CREATED)

                comment.type = Comment.REQUEST
                comment.rel_content_type = ContentType.objects.get_for_model(new_request)
                comment.rel_object_id = new_request.pk

            elif form.cleaned_data.get('status'):
                comment.type = Comment.STATUS
                obj.status = form.cleaned_data.get('status')
                obj.comment = comment.body
                obj.save()
                set_comment(type(obj).STATUS_CHANGED)
            else:
                comment.type = Comment.USER
            comment.save()
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(obj.get_absolute_url())


class ReplyView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, object_id, parent_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=object_id)
        form = CommentForm(request.POST)

        if form.is_valid():
            Comment.objects.create(
                type=Comment.USER,
                user=request.user,
                content_type=content_type,
                object_id=object_id,
                parent_id=parent_id,
                body=form.cleaned_data.get('body'),
                is_public=form.cleaned_data.get('is_public')
            )
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(obj.get_absolute_url())
