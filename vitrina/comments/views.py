from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.comments.forms import CommentForm
from vitrina.comments.helpers import create_task, create_subscription, send_mail_and_create_tasks_for_subs
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class
from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain, prepare_email_by_identifier, send_email_with_logging
from vitrina.orgs.models import Representative
from vitrina.plans.models import Plan
from vitrina.requests.models import Request, RequestObject, RequestAssignment
from vitrina.resources.models import DatasetDistribution
from vitrina.tasks.models import Task
from django.utils.translation import gettext_lazy as _



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
                user_org = request.user.organization
                comment.type = Comment.STATUS
                if isinstance(obj, Request):
                    user_org = request.user.organization
                    request_assignment = RequestAssignment.objects.filter(
                        organization=user_org,
                        request=obj
                    ).first()
                    obj.status = status
                    obj.comment = comment.body
                    obj.save()
                    set_comment(type(obj).STATUS_CHANGED)
                    if not request_assignment:
                        if user_org and status==Request.APPROVED:
                            request_assignment = RequestAssignment(
                                request=obj,
                                organization=user_org,
                                status=Request.APPROVED
                            )
                            request_assignment.save()
                            messages.info(request, _("Jūsų organizaciją įtraukta į poreikių organizacijų sąrašą"))
                        else:
                            messages.error(request, _("Jūsų organizaciją nėra įtraukta į poreikių organizacijų sąrašą"))
                            return redirect(obj.get_absolute_url())
                    if status == Request.OPENED:
                        obj.status = status
                        obj.comment = comment.body
                        obj.save()
                        set_comment(type(obj).STATUS_CHANGED)
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
                    if status == Request.APPROVED:
                        obj.status = status
                        obj.comment = comment.body
                        obj.save()
                        set_comment(type(obj).STATUS_CHANGED)
                    if status == Request.REJECTED:
                        approved_assignments_exists = RequestAssignment.objects.filter(
                            status=Request.APPROVED,
                            request=obj
                        )
                        opened_assignments_exists = RequestAssignment.objects.filter(
                            status=Request.OPENED,
                            request=obj
                        )
                        if not approved_assignments_exists and not opened_assignments_exists:
                            obj.status = status
                            obj.comment = comment.body
                            obj.save()
                            set_comment(type(obj).STATUS_CHANGED)
                    ra_comment = form.save(commit=False)
                    request_assignment.status = status
                    request_assignment.comment = ra_comment.body
                    ra_comment.content_type = ContentType.objects.get_for_model(RequestAssignment)
                    ra_comment.object_id = request_assignment.pk
                    request_assignment.save()
                    ra_comment.save()
                else:
                    obj.status = status
                    obj.comment = comment.body
                    obj.save()
                    set_comment(type(obj).STATUS_CHANGED)
            else:
                comment.type = Comment.USER
            comment.save()
            create_task("New", content_type, obj.pk, request.user, obj=obj)
            create_subscription(request.user, comment)
            send_mail_and_create_tasks_for_subs("New", content_type, obj.pk, request.user, obj=obj)
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(obj.get_absolute_url())


class ReplyView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, object_id, parent_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=object_id)
        form = CommentForm(obj, request.POST)

        if form.is_valid():
            comment = Comment.objects.create(
                type=Comment.USER,
                user=request.user,
                content_type=content_type,
                object_id=object_id,
                parent_id=parent_id,
                body=form.cleaned_data.get('body'),
                is_public=form.cleaned_data.get('is_public'),
            )
            comment_ct = ContentType.objects.get_for_model(comment)
            parent_comment = Comment.objects.get(pk=parent_id)
            create_task("Reply", content_type, object_id, request.user, obj=obj,
                        comment_object=comment, comment_ct=comment_ct)
            create_subscription(request.user, comment)

            send_mail_and_create_tasks_for_subs("Reply", comment_ct, parent_id,
                                                request.user, obj=obj, comment_object=parent_comment)
            comment_task = Task.objects.filter(
                comment_object=parent_comment
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
                send_email_with_logging(email_data, [emails])
                set_comment(Request.CREATED)
                comment.rel_content_type = ContentType.objects.get_for_model(new_request)
                comment.rel_object_id = new_request.pk
                comment.type = Comment.REQUEST
            create_task("New", external_content_type, external_object_id, request.user)
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
            create_task("Reply", external_content_type, parent_id, request.user)
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(reverse('object-data', kwargs={
            'pk': form.data.get('dataset_id'),
            'model': external_content_type,
            'uuid': external_object_id,
        }))
