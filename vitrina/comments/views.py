from django.utils import timezone

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.comments.forms import CommentForm
from vitrina.comments.helpers import (
    create_task,
    create_subscription,
    send_mail_and_create_tasks_for_subs,
    NEW_COMMENT,
    REPLY_COMMENT,
    save_request_comment,
)
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class, has_comment_permission
from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain, email
from vitrina.messages.models import Subscription
from vitrina.orgs.models import Representative, Organization
from vitrina.plans.models import Plan
from vitrina.requests.models import Request, RequestObject, RequestAssignment, RequestEscalation
from vitrina.resources.models import DatasetDistribution
from vitrina.requests.tasks.escalation import start_escalation_for_request
from vitrina.structure.models import Property, Model
from vitrina.tasks.models import Task
from vitrina.users.models import User
from django.utils.translation import gettext_lazy as _


class CommentView(LoginRequiredMixin, PermissionRequiredMixin, RevisionMixin, View):
    content_type: ContentType
    obj: Model

    @staticmethod
    def _update_request_assignment(form, comment, request_assignment, status):
        ra_comment = form.save(commit=False)
        ra_comment.content_type = ContentType.objects.get_for_model(RequestAssignment)
        ra_comment.object_id = request_assignment.pk

        request_assignment.status = status
        request_assignment.comment = ra_comment.body
        request_assignment.save()
        ra_comment.save()

    @staticmethod
    def _handle_form_errors(request, form):
        error_messages = [error[0] for error in form.errors.values()]
        messages.error(request, "\n".join(error_messages))

    @staticmethod
    def _get_publisher_representative_emails(publisher_org):
        users = User.objects.filter(organization=publisher_org, status=User.ACTIVE)
        return [user.email for user in users if user.email]

    @staticmethod
    def _should_close_plan(plan):
        all_requests_opened = (
            plan.planrequest_set.filter(request__status=Request.OPENED).count() == plan.planrequest_set.count()
        )

        all_datasets_have_distributions = (
            plan.plandataset_set.annotate(
                has_distributions=Exists(
                    DatasetDistribution.objects.filter(
                        dataset_id=OuterRef("dataset_id"),
                    )
                )
            )
            .filter(has_distributions=True)
            .count()
            == plan.plandataset_set.count()
        )

        return all_requests_opened and all_datasets_have_distributions

    def dispatch(self, request, *args, **kwargs):
        self.content_type = get_object_or_404(ContentType, pk=kwargs.get("content_type_id"))
        self.obj = get_object_or_404(self.content_type.model_class(), pk=kwargs.get("object_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_comment_permission(self.obj, self.request.user)

    def _handle_request_registration(self, form, comment, request):
        new_request = self._create_request(form, comment)
        self._create_request_assignment(new_request, request)

        comment.type = Comment.REQUEST
        comment.rel_content_type = ContentType.objects.get_for_model(new_request)
        comment.rel_object_id = new_request.pk
        comment.save()

        if email_recipients := self._collect_request_email_recipients(new_request):
            self._send_request_creation_emails(email_recipients, new_request, request)

        start_escalation_for_request(new_request)

        self._finalize_comment(comment, request, excluded_emails=email_recipients)
        return redirect(self.obj.get_absolute_url())

    def _collect_request_email_recipients(self, new_request):
        if not isinstance(self.obj, Dataset):
            return []

        recipients = []
        recipients.extend(self._get_dataset_organization_email())
        recipients.extend(self._get_subscription_emails())
        recipients.extend(self._get_publisher_organization_emails())

        return list(set(recipients))  # Remove duplicates

    def _get_dataset_organization_email(self):
        if self.obj.organization and self.obj.organization.email:
            return [self.obj.organization.email]
        return []

    def _get_subscription_emails(self):
        emails = []
        content_type = ContentType.objects.get_for_model(self.obj)

        subs = Subscription.objects.filter(
            Q(object_id=self.obj.pk) | Q(object_id=None),
            sub_type=Subscription.DATASET,
            content_type=content_type,
            dataset_comments_sub=True,
        )
        for sub in subs:
            if self._should_include_subscription_email(sub, content_type):
                emails.append(sub.user.email)

        return emails

    def _should_include_subscription_email(self, subscription, content_type):
        if not subscription.user.email or not subscription.email_subscribed:
            return False

        return Representative.objects.filter(
            content_type=content_type,
            object_id=self.obj.pk,
            email=subscription.user.email,
        ).exists()

    def _get_publisher_organization_emails(self):
        emails = []

        publisher_org = Organization.objects.filter(id=self.obj.publisher_id).first()
        if not publisher_org:
            return emails

        if publisher_org.email:
            emails.append(publisher_org.email)

        return emails

    def _create_request(self, form, comment):
        frequency = form.cleaned_data.get("increase_frequency")
        title = form.cleaned_data.get("request_title") or self._get_request_title()

        new_request = Request.objects.create(
            status=Request.CREATED,
            user=comment.user,
            title=title,
            description=comment.body,
            periodicity=frequency.title if frequency else "",
        )

        RequestObject.objects.create(
            request=new_request,
            object_id=self.obj.pk,
            content_type=self.content_type,
        )

        set_comment(Request.CREATED)
        return new_request

    def _create_request_assignment(self, new_request, request):
        organization = self._get_organization_for_assignment()

        if not organization:
            return

        RequestAssignment.objects.create(
            request=new_request,
            organization=organization,
            status=Request.CREATED,
        )

    def _get_organization_for_assignment(self):
        obj = self.obj

        if isinstance(obj, Model) and obj.dataset.organization:
            return obj.dataset.organization

        if isinstance(obj, Property) and obj.model.dataset.organization:
            return obj.model.dataset.organization

        if isinstance(obj, Dataset) and obj.organization:
            return obj.organization

        return None

    def _get_request_title(self):
        if hasattr(self.obj, "title") and self.obj.title:
            return self.obj.title
        if hasattr(self.obj, "name"):
            return self.obj.name
        return ""

    def _handle_status_change(self, form, comment, status, request):
        comment.type = Comment.STATUS

        if isinstance(self.obj, Request):
            return self._handle_request_status_change(form, comment, status, request)

        return self._handle_non_request_status_change(comment, status, request)

    def _handle_request_status_change(self, form, comment, status, request):
        if status == Request.REJECTED and not self._can_reject_request():
            messages.error(request, _("Cannot reject - approved/opened assignments exist"))
            return redirect(self.obj.get_absolute_url())

        self._update_request_status(status, comment.body, request.user)

        user_org = request.user.organization
        request_assignment = RequestAssignment.objects.filter(organization=user_org, request=self.obj).first()

        if not request_assignment and status == Request.APPROVED:
            if not user_org:
                messages.error(
                    request,
                    _("Jūsų organizaciją nėra įtraukta į poreikių organizacijų sąrašą"),
                )
                return redirect(self.obj.get_absolute_url())

            request_assignment = RequestAssignment.objects.create(
                request=self.obj,
                organization=user_org,
                status=Request.APPROVED,
            )
            messages.info(
                request,
                _("Jūsų organizaciją įtraukta į poreikių organizacijų sąrašą"),
            )

        if status == Request.OPENED:
            self._handle_opened_status()

        if request_assignment:
            self._update_request_assignment(form, comment, request_assignment, status)

        comment.save()
        self._finalize_comment(comment, request)
        return redirect(self.obj.get_absolute_url())

    def _update_request_status(self, status, body, user):
        save_request_comment(self.obj, status, body, user)
        self.obj.status = status
        self.obj.save()
        set_comment(type(self.obj).STATUS_CHANGED)

    def _handle_opened_status(self):
        request_plans = Plan.objects.filter(planrequest__request=self.obj)

        for plan in request_plans:
            if self._should_close_plan(plan):
                plan.is_closed = True
                plan.save()

    def _can_reject_request(self):
        approved_exists = RequestAssignment.objects.filter(status=Request.APPROVED, request=self.obj).exists()

        opened_exists = RequestAssignment.objects.filter(status=Request.OPENED, request=self.obj).exists()

        return not approved_exists and not opened_exists

    def _handle_non_request_status_change(self, comment, status, request):
        save_request_comment(self.obj, status, comment.body, request.user)
        self.obj.status = status
        self.obj.save()
        set_comment(type(self.obj).STATUS_CHANGED)

        comment.save()
        self._finalize_comment(comment, request)
        return redirect(self.obj.get_absolute_url())

    def _get_form(self, request):
        form_class = get_comment_form_class(self.obj, request.user)
        return form_class(self.obj, request.POST)

    def _handle_regular_comment(self, comment, request):
        comment.type = Comment.USER
        comment.save()

        self._finalize_comment(comment, request)
        return redirect(self.obj.get_absolute_url())

    def _finalize_comment(self, comment, request, excluded_emails=None):
        if excluded_emails is None:
            excluded_emails = []

        link = self._get_object_link()
        create_task(NEW_COMMENT, self.content_type, self.obj.pk, request.user, obj=self.obj)
        create_subscription(request.user, comment)
        send_mail_and_create_tasks_for_subs(
            NEW_COMMENT,
            self.content_type,
            self.obj.pk,
            request.user,
            link,
            obj=self.obj,
            excluded_emails=excluded_emails,
            text=comment.body,
        )

        if isinstance(self.obj, Request):
            self._check_and_stop_escalation(request.user)

    def _check_and_stop_escalation(self, user):
        try:
            escalation = self.obj.escalation
        except RequestEscalation.DoesNotExist:
            return

        if not escalation.is_active:
            return

        if user.email in escalation.recipients_at_current_level:
            escalation.stop_escalation(RequestEscalation.STOP_REASON_RESPONDED)

    def _get_object_link(self):
        return "%s%s" % (get_current_domain(self.request), self.obj.get_absolute_url())

    def _send_request_creation_emails(self, recipients, new_request, request):
        email(
            recipients,
            "request-created-sub",
            "vitrina/emails/request_created_organization_sub.md",
            {
                "request": new_request.title,
                "link": get_current_domain(request) + new_request.get_absolute_url(),
            },
        )

    def _create_base_comment(self, form, user, content_type_id, object_id):
        comment = form.save(commit=False)
        comment.user = user
        comment.content_type = self.content_type
        comment.object_id = object_id
        return comment

    def post(self, request, content_type_id, object_id):
        form = self._get_form(request)

        if not form.is_valid():
            self._handle_form_errors(request, form)
            return redirect(self.obj.get_absolute_url())

        comment = self._create_base_comment(form, request.user, content_type_id, object_id)

        if form.cleaned_data.get("register_request"):
            return self._handle_request_registration(form, comment, request)

        if status := form.cleaned_data.get("status"):
            return self._handle_status_change(form, comment, status, request)

        return self._handle_regular_comment(comment, request)


class ReplyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    content_type: ContentType
    obj: Model

    def dispatch(self, request, *args, **kwargs):
        self.content_type = get_object_or_404(ContentType, pk=kwargs.get("content_type_id"))
        self.obj = get_object_or_404(self.content_type.model_class(), pk=kwargs.get("object_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_comment_permission(self.obj, self.request.user)

    def post(self, request, content_type_id, object_id, parent_id):
        content_type = self.content_type
        obj = self.obj
        form = CommentForm(obj, request.POST)

        if form.is_valid():
            link = "%s%s" % (get_current_domain(self.request), obj.get_absolute_url())
            comment = Comment.objects.create(
                type=Comment.USER,
                user=request.user,
                content_type=content_type,
                object_id=object_id,
                parent_id=parent_id,
                body=form.cleaned_data.get("body"),
                is_public=form.cleaned_data.get("is_public"),
            )
            comment_ct = ContentType.objects.get_for_model(comment)
            parent_comment = Comment.objects.get(pk=parent_id)
            create_task(
                REPLY_COMMENT,
                content_type,
                object_id,
                request.user,
                obj=obj,
                comment_object=comment,
                comment_ct=comment_ct,
            )
            create_subscription(request.user, comment)

            send_mail_and_create_tasks_for_subs(
                REPLY_COMMENT,
                comment_ct,
                parent_id,
                request.user,
                link,
                obj=obj,
                comment_object=parent_comment,
                text=comment.body,
            )
            comment_task = Task.objects.filter(comment_object=parent_comment).first()
            if comment_task:
                comment_task.status = Task.COMPLETED
                comment_task.completed = timezone.now()
                comment_task.save()
        else:
            messages.error(request, "\n".join([error[0] for error in form.errors.values()]))
        return redirect(obj.get_absolute_url())


class ExternalCommentView(LoginRequiredMixin, PermissionRequiredMixin, RevisionMixin, View):
    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("dataset_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_comment_permission(self.dataset, self.request.user)

    def post(self, request, dataset_id, external_content_type, external_object_id):
        form_class = get_comment_form_class()
        form = form_class(external_object_id, request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.external_object_id = external_object_id
            comment.external_content_type = external_content_type
            comment.type = Comment.USER
            sub_email_list = []

            if form.cleaned_data.get("register_request"):
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
                if self.dataset.organization:
                    RequestAssignment.objects.create(
                        request=new_request,
                        organization=self.dataset.organization,
                        status=Request.CREATED,
                    )
                set_comment(Request.CREATED)
                comment.rel_content_type = ContentType.objects.get_for_model(new_request)
                comment.rel_object_id = new_request.pk
                comment.type = Comment.REQUEST

                if self.dataset.organization and self.dataset.organization.email:
                    sub_email_list.append(self.dataset.organization.email)

                subs = Subscription.objects.filter(
                    Q(object_id=self.dataset.pk) | Q(object_id=None),
                    sub_type=Subscription.DATASET,
                    content_type=ContentType.objects.get_for_model(self.dataset),
                    dataset_comments_sub=True,
                )
                for sub in subs:
                    if (
                        sub.user.email
                        and sub.email_subscribed
                        and sub.user.email not in sub_email_list
                        and Representative.objects.filter(
                            content_type=ContentType.objects.get_for_model(self.dataset),
                            object_id=self.dataset.pk,
                            email=sub.user.email,
                        ).exists()
                    ):
                        sub_email_list.append(sub.user.email)

                if publisher := Organization.objects.filter(id=self.dataset.publisher_id).first():
                    sub_email_list.append(publisher.email)
                if sub_email_list:
                    email(
                        sub_email_list,
                        "request-created-sub",
                        "vitrina/emails/request_created_organization_sub.md",
                        {
                            "request": new_request.title,
                            "link": get_current_domain(self.request) + new_request.get_absolute_url(),
                        },
                    )
            else:
                representatives = Representative.objects.filter(
                    content_type=ContentType.objects.get_for_model(Dataset),
                    object_id=dataset_id,
                )
                dataset = Dataset.objects.get(pk=dataset_id)
                emails = []
                title = f"Klaida duomenyse: {external_object_id}, {dataset.name}/{external_content_type}"
                for rep in representatives:
                    emails.append(rep.email)
                    Task.objects.create(
                        title=title,
                        description=f"Aptikta klaida duomenyse {external_object_id},"
                        f" {dataset.name}/{external_content_type}.",
                        user=rep.user,
                        status=Task.CREATED,
                        type=Task.ERROR,
                    )

                url = (
                    f"{get_current_domain(self.request)}/datasets/"
                    f"{dataset_id}/data/{external_content_type}/{external_object_id}"
                )
                email(
                    emails,
                    "error-in-data",
                    "vitrina/comments/emails/sub/comment_about_error_in_data.md",
                    {"title": dataset.title, "url": url},
                )
            create_task(NEW_COMMENT, external_content_type, external_object_id, request.user)
            comment.save()
        else:
            messages.error(request, "\n".join([error[0] for error in form.errors.values()]))
        return redirect(
            reverse(
                "object-data",
                kwargs={
                    "pk": form.data.get("dataset_id"),
                    "model": external_content_type,
                    "uuid": external_object_id,
                },
            )
        )


class ExternalReplyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    dataset: Dataset

    def has_permission(self):
        return True

    def post(self, request, external_content_type, external_object_id, parent_id):
        form = CommentForm(None, request.POST)

        if dataset_id := form.data.get("dataset_id"):
            dataset = get_object_or_404(Dataset, pk=dataset_id)
            if has_comment_permission(dataset, request.user):
                if form.is_valid():
                    Comment.objects.create(
                        type=Comment.USER,
                        user=request.user,
                        external_object_id=external_object_id,
                        external_content_type=external_content_type,
                        parent_id=parent_id,
                        body=form.cleaned_data.get("body"),
                        is_public=form.cleaned_data.get("is_public"),
                    )
                    create_task(REPLY_COMMENT, external_content_type, parent_id, request.user)
                else:
                    messages.error(request, "\n".join([error[0] for error in form.errors.values()]))
                return redirect(
                    reverse(
                        "object-data",
                        kwargs={
                            "pk": form.data.get("dataset_id"),
                            "model": external_content_type,
                            "uuid": external_object_id,
                        },
                    )
                )

        return self.handle_no_permission()


class OwnerOrSuperuserQuerysetMixin:
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_authenticated:
            return qs.none()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(**{f"{self.owner_field}_id": self.request.user.id})


class CommentDeleteView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        queryset = Comment.objects.all()

        if not request.user.is_superuser:
            queryset = queryset.filter(user=request.user)

        try:
            comment = queryset.get(pk=pk)

            comment.deleted = True
            comment.deleted_on = timezone.now()
            comment.save()

            return JsonResponse({"success": True})
        except Comment.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)


class CommentEditView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        queryset = Comment.objects.all()

        if not request.user.is_superuser:
            queryset = queryset.filter(user=request.user)

        try:
            comment = queryset.get(pk=pk)

            body = request.POST.get("body", "").strip()
            if not body:
                return JsonResponse({"error": "Body is required"}, status=400)

            comment.body = body
            comment.is_public = "is_public" in request.POST
            comment.edited_at = timezone.now()
            comment.save()

            return JsonResponse({"success": True, "body": comment.body, "is_public": comment.is_public})
        except Comment.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)
