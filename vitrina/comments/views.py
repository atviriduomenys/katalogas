from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from reversion import set_comment
from reversion.views import RevisionMixin
from django.utils.translation import gettext_lazy as _

from vitrina import settings
from vitrina.comments.forms import CommentForm
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class
from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain, prepare_email_by_identifier
from vitrina.orgs.models import Representative
from vitrina.plans.models import Plan
from vitrina.requests.models import Request, RequestObject
from vitrina.resources.models import DatasetDistribution
from vitrina.tasks.models import Task
from vitrina.users.models import User


class CommentView(
    LoginRequiredMixin,
    RevisionMixin,
    View
):
    def post(self, request, content_type_id, object_id):
        email_content = """
            Sveiki, <br>
            portale užregistruotas naujas pasiūlymas/pastaba: <br>
            Pasiūlymo/pastabos teikėjo vardas: {0} <br>
            Pasiūlymas/pastaba: {1}        
        """
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
                title = obj.title
                if not title and hasattr(obj, 'name'):
                    title = obj.name
                new_request = Request.objects.create(
                    status=Request.CREATED,
                    user=request.user,
                    title=title,
                    description=comment.body,
                    periodicity=frequency.title if frequency else "",
                )
                if hasattr(obj, 'organization'):
                    new_request.organizations.add(obj.organization)
                RequestObject.objects.create(
                    request=new_request,
                    object_id=object_id,
                    content_type=content_type,
                )
                new_request.save()
                set_comment(Request.CREATED)

                comment.type = Comment.REQUEST
                comment.rel_content_type = ContentType.objects.get_for_model(new_request)
                comment.rel_object_id = new_request.pk

            elif status := form.cleaned_data.get('status'):
                comment.type = Comment.STATUS
                obj.status = status
                obj.comment = comment.body
                obj.save()
                set_comment(type(obj).STATUS_CHANGED)

                if isinstance(obj, Request) and status == Request.OPENED:
                    request_plans = Plan.objects.filter(planrequest__request=obj)

                    for plan in request_plans:
                        if (
                            plan.planrequest_set.filter(
                                request__status=Request.OPENED
                            ).count() == plan.planrequest_set.count() and
                            plan.plandataset_set.annotate(
                                has_distributions=Exists(DatasetDistribution.objects.filter(
                                    dataset_id=OuterRef('dataset_id'),
                                ))
                            ).count() == plan.plandataset_set.count()
                        ):
                            plan.is_closed = True
                            plan.save()
                if obj is not None:
                    if obj.status == 'REJECTED':
                        email_data = prepare_email_by_identifier('application-use-case-rejected', email_content,
                                                                 'Gautas naujas pasiūlymas',
                                                                 [obj.title, obj.description])
                        if obj.user is not None:
                            if obj.user.email is not None:
                                send_mail(
                                    subject=_(email_data['email_subject']),
                                    message=_(email_data['email_content']),
                                    from_email=settings.DEFAULT_FROM_EMAIL,
                                    recipient_list=[obj.user.email],
                                )
            else:
                comment.type = Comment.USER
            comment.save()
            Task.objects.create(
                title=f"Parašytas komentaras objektui: {content_type}, id: {obj.pk}",
                organization=obj.organization if hasattr(obj, 'organization') else None,
                description=f"Prie {content_type} {obj.pk} parašytas naujas komentaras.",
                content_type=content_type,
                object_id=obj.pk,
                status=Task.CREATED,
                user=request.user,
                type=Task.COMMENT
            )
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(obj.get_absolute_url())


class ReplyView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, object_id, parent_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=object_id)
        form = CommentForm(obj, request.POST)

        if form.is_valid():
            comm = Comment.objects.create(
                type=Comment.USER,
                user=request.user,
                content_type=content_type,
                object_id=object_id,
                parent_id=parent_id,
                body=form.cleaned_data.get('body'),
                is_public=form.cleaned_data.get('is_public'),
            )
            comm_ct = ContentType.objects.get_for_model(comm)
            parent_comm = Comment.objects.get(pk=parent_id)
            Task.objects.create(
                title=f"Parašytas atsakymas komentarui: {comm_ct}, id: {parent_id}",
                organization=obj.organization if hasattr(obj, 'organization') else None,
                description=f"Komentarui {parent_id} parašytas naujas atsakymas.",
                content_type=content_type,
                object_id=object_id,
                comment_object=comm,
                status=Task.CREATED,
                user=request.user,
                type=Task.COMMENT
            )
            comment_task = Task.objects.filter(
                comment_object=parent_comm
            ).first()
            if comment_task:
                comment_task.status = Task.COMPLETED
                comment_task.completed = datetime.now(timezone.utc)
                comment_task.save()
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(obj.get_absolute_url())


class ExternalCommentView(
    LoginRequiredMixin,
    RevisionMixin,
    View
):
    def post(self, request, dataset_id, external_content_type, external_object_id):
        form_class = get_comment_form_class()
        form = form_class(external_object_id, request.POST)
        base_email_content = """
            Gautas pranešimas, kad duomenyse yra klaida:
            {0}
            Klaida užregistruota objektui: {1},
            {2}/{3}'
        """
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.external_object_id = external_object_id
            comment.external_content_type = external_content_type
            comment.type = Comment.USER

            if form.cleaned_data.get('register_request'):
                new_request = Request.objects.create(
                    status=Request.CREATED,
                    user=request.user,
                    title=external_object_id,
                    description=comment.body,
                )
                RequestObject.objects.create(
                    request=new_request,
                    object_id=dataset_id,
                    content_type=ContentType.objects.get_for_model(Dataset),
                    external_object_id=external_object_id,
                    external_content_type=external_content_type,
                )
                representatives = Representative.objects.filter(
                    content_type=ContentType.objects.get_for_model(Dataset),
                    object_id=dataset_id)
                dataset = Dataset.objects.get(pk=dataset_id)
                emails = []
                title = f'Klaida duomenyse: {external_object_id}, {dataset.name}/{external_content_type}'
                for rep in representatives:
                    emails.append(rep.email)
                    Task.objects.create(
                        title=title,
                        description=f"Aptikta klaida duomenyse {external_object_id},"
                                    f" {dataset.name}/{external_content_type}.",
                        user=rep.user,
                        status=Task.CREATED,
                        type=Task.ERROR
                    )

                url = f"{get_current_domain(self.request)}/datasets/" \
                      f"{dataset_id}/data/{external_content_type}/{external_object_id}"
                email_data = prepare_email_by_identifier('error-in-data', base_email_content, title,
                                                         [url, external_object_id, dataset.name, external_content_type])
                send_mail(
                    subject=email_data['email_subject'],
                    message=email_data['email_content'],
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[emails],
                )
                set_comment(Request.CREATED)
                comment.rel_content_type = ContentType.objects.get_for_model(new_request)
                comment.rel_object_id = new_request.pk
                comment.type = Comment.REQUEST

            Task.objects.create(
                title=f"Parašytas komentaras objektui: {external_content_type}, id: {external_object_id}",
                description=f"Parašytas naujas komentaras {external_content_type}, id: {external_object_id}.",
                status=Task.CREATED,
                user=request.user,
                type=Task.COMMENT
            )
            comment.save()
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(reverse('object-data', kwargs={
            'pk': form.data.get('dataset_id'),
            'model': external_content_type,
            'uuid': external_object_id,
        }))


class ExternalReplyView(LoginRequiredMixin, View):
    def post(self, request, external_content_type, external_object_id, parent_id):
        form = CommentForm(None, request.POST)

        if form.is_valid():
            Comment.objects.create(
                type=Comment.USER,
                user=request.user,
                external_object_id=external_object_id,
                external_content_type=external_content_type,
                parent_id=parent_id,
                body=form.cleaned_data.get('body'),
                is_public=form.cleaned_data.get('is_public')
            )
            Task.objects.create(
                title=f"Parašytas atsakymas komentarui: {external_content_type}, id: {parent_id}",
                description=f"Atsakyta į komentarą {external_content_type}, id: {parent_id}.",
                content_type=external_content_type,
                object_id=parent_id,
                status=Task.CREATED,
                user=request.user,
                type=Task.COMMENT
            )
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(reverse('object-data', kwargs={
            'pk': form.data.get('dataset_id'),
            'model': external_content_type,
            'uuid': external_object_id,
        }))
