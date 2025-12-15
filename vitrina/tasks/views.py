import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.forms import BaseForm
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, DeleteView, TemplateView, ListView
from django.utils.translation import gettext_lazy as _

from vitrina.helpers import get_filter_url
from vitrina.orgs.models import Organization
from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks

from vitrina.users.models import User

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Value, Case, When, CharField, Count
from django.db.models.functions import Concat


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "vitrina/tasks/list.html"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user_pk = kwargs.get("pk")

        if not (request.user.is_staff or request.user.is_superuser):
            if request.user.pk != user_pk:
                raise PermissionDenied("You can only view your own tasks")

        self.viewed_user = get_object_or_404(User, pk=user_pk)
        return super().dispatch(request, *args, **kwargs)

    @property
    def target_user(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return self.viewed_user
        return self.request.user

    @property
    def filter_params(self):
        return {
            "owner": self.request.GET.get("owner", "all"),
            "status": self.request.GET.get("status", ""),
            "type": self.request.GET.get("type", ""),
            "keyword": self.request.GET.get("q", ""),
        }

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = self._optimize_queryset(queryset)
        queryset = get_active_tasks(self.target_user, queryset, all_tasks=True)
        queryset = self._apply_filters(queryset)
        return queryset.order_by("due_date")

    def _optimize_queryset(self, queryset):
        return queryset.select_related("user", "organization", "content_type")

    def _apply_filters(self, queryset):
        params = self.filter_params

        if params["owner"] == "user":
            queryset = queryset.filter(user__pk=self.target_user.pk)

        if params["status"]:
            queryset = queryset.filter(status=params["status"])

        if params["type"]:
            queryset = self._apply_type_filter(queryset, params["type"])

        if params["keyword"]:
            queryset = self._apply_keyword_search(queryset, params["keyword"])

        return queryset

    def _apply_type_filter(self, queryset, type_value):
        return queryset.annotate(task_type=self._get_task_type_annotation()).filter(task_type=type_value)

    def _apply_keyword_search(self, queryset, keyword):
        return queryset.annotate(user_name=Concat("user__first_name", Value(" "), "user__last_name")).filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(organization__title__icontains=keyword)
            | Q(user_name__icontains=keyword)
        )

    @staticmethod
    def _get_task_type_annotation():
        return Case(
            When(type=Task.ERROR_FREQUENCY, then=Value(Task.ERROR)),
            When(type=Task.ERROR_DISTRIBUTION, then=Value(Task.ERROR)),
            When(type=Task.ERROR_GEOPORTAL, then=Value(Task.ERROR)),
            default=F("type"),
            output_field=CharField(),
        )

    def _get_base_queryset_for_counts(self):
        queryset = Task.objects.all()
        queryset = self._optimize_queryset(queryset)
        queryset = get_active_tasks(self.target_user, queryset, all_tasks=True)

        params = self.filter_params

        if params["keyword"]:
            queryset = self._apply_keyword_search(queryset, params["keyword"])

        return queryset

    def _calculate_filter_counts(self):
        base_queryset = self._get_base_queryset_for_counts()
        params = self.filter_params

        status_queryset = base_queryset
        if params["type"]:
            status_queryset = self._apply_type_filter(status_queryset, params["type"])

        type_queryset = base_queryset.annotate(task_type=self._get_task_type_annotation())
        if params["status"]:
            type_queryset = type_queryset.filter(status=params["status"])

        owner_status_counts = status_queryset.aggregate(
            user_tasks_count=Count("id", filter=Q(user__pk=self.target_user.pk)),
            all_tasks_count=Count("id"),
            **{
                f"status_{status_value}_count": Count("id", filter=Q(status=status_value))
                for status_value in Task.FILTER_STATUSES.keys()
            },
        )

        type_counts = type_queryset.aggregate(
            **{
                f"type_{type_value}_count": Count("id", filter=Q(task_type=type_value))
                for type_value in Task.FILTER_TYPES.keys()
            }
        )

        return {**owner_status_counts, **type_counts}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
        }

        params = self.filter_params

        counts = self._calculate_filter_counts()

        context["filters"] = self._build_filters(params, counts)
        context["search_url"] = reverse("user-task-list", args=[self.target_user.pk])
        context["search_query"] = dict(self.request.GET.copy())
        context["q"] = params["keyword"]

        return context

    def _build_filters(self, params, counts):
        return [
            self._build_owner_filter(params, counts),
            self._build_status_filter(params, counts),
            self._build_type_filter(params, counts),
        ]

    def _build_owner_filter(self, params, counts):
        return {
            "title": _("Vykdytojas"),
            "items": [
                {
                    "title": _("Mano užduotys"),
                    "url": get_filter_url(
                        self.request,
                        "owner",
                        "user",
                        params["owner"] == "user",
                        facet_field=False,
                    ),
                    "count": counts["user_tasks_count"],
                    "selected": params["owner"] == "user",
                    "always_show": True,
                },
                {
                    "title": _("Visos užduotys"),
                    "url": get_filter_url(
                        self.request,
                        "owner",
                        "all",
                        params["owner"] == "all",
                        facet_field=False,
                    ),
                    "count": counts["all_tasks_count"],
                    "selected": params["owner"] == "all",
                    "always_show": True,
                },
            ],
        }

    def _build_status_filter(self, params, counts):
        return {
            "title": _("Būsena"),
            "items": [
                {
                    "title": title,
                    "url": get_filter_url(
                        self.request,
                        "status",
                        value,
                        params["status"] == value,
                        facet_field=False,
                    ),
                    "count": counts.get(f"status_{value}_count", 0),
                    "selected": params["status"] == value,
                }
                for value, title in Task.FILTER_STATUSES.items()
            ],
        }

    def _build_type_filter(self, params, counts):
        return {
            "title": _("Tipas"),
            "items": [
                {
                    "title": title,
                    "url": get_filter_url(
                        self.request,
                        "type",
                        value,
                        params["type"] == value,
                        facet_field=False,
                    ),
                    "count": counts.get(f"type_{value}_count", 0),
                    "selected": params["type"] == value,
                }
                for value, title in Task.FILTER_TYPES.items()
            ],
        }


class TaskView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "vitrina/tasks/detail.html"
    pk_url_kwarg = "task_id"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        self.object = get_object_or_404(Task, pk=kwargs.get("task_id"))

        if request.user.is_staff or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        user_tasks = get_active_tasks(request.user, all_tasks=True)
        if not user_tasks.filter(pk=self.object.pk).exists():
            raise PermissionDenied("You don't have permission to view this task")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object

        context["org"] = None
        if task.organization_id:
            context["org"] = (
                Organization.objects.filter(pk=task.organization_id).values_list("title", flat=True).first()
            )

        context["object_url"] = task.content_object.get_absolute_url if task.content_object else None

        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("user-task-list", args=[self.request.user.pk]): _("Užduotys"),
        }

        return context


class CloseTaskView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Task
    template_name = "confirm_close.html"

    pk_url_kwarg = "task_id"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Task, pk=self.kwargs.get("task_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            user_tasks = get_active_tasks(self.request.user, all_tasks=True)
            if user_tasks.filter(pk=self.object.pk) and self.object.status != Task.COMPLETED:
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Užduoties uždarymas")
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        self.object.status = Task.COMPLETED
        self.object.completed = datetime.datetime.now()
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("user-task-list", kwargs={"pk": self.request.user.pk})


class AssignTaskView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "confirm_reassign.html"
    pk_url_kwarg = "task_id"

    def dispatch(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=self.kwargs.get("task_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            user_tasks = get_active_tasks(self.request.user, all_tasks=True)
            if user_tasks.filter(pk=self.task.pk) and self.task.status != Task.COMPLETED:
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = self.task
        context["current_title"] = _("Užduoties priskyrimas")
        return context

    def post(self, request, *args, **kwargs):
        if self.task is not None:
            self.task.user = self.request.user
            self.task.status = Task.ASSIGNED
            self.task.assigned = datetime.datetime.now()
            self.task.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("user-task-list", kwargs={"pk": self.request.user.pk})
