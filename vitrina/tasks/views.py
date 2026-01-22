import datetime
from django.utils.functional import cached_property
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.forms import BaseForm
from django.http import HttpResponseRedirect, HttpResponse
from django.http.request import HttpRequest
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
from django.db.models import Q, F, Value, Case, When, CharField, Count, QuerySet
from django.db.models.functions import Concat


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "vitrina/tasks/list.html"
    paginate_by = 20

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        is_privileged = request.user.is_staff or request.user.is_superuser

        if not is_privileged and request.user.pk != kwargs.get("pk"):
            raise PermissionDenied("You can only view your own tasks")

        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def target_user(self) -> User:
        if self.request.user.is_staff or self.request.user.is_superuser:
            return get_object_or_404(User, pk=self.kwargs.get("pk"))
        return self.request.user

    @cached_property
    def filter_params(self) -> dict[str, str]:
        return {
            "owner": self.request.GET.get("owner", "all"),
            "status": self.request.GET.get("status", ""),
            "type": self.request.GET.get("type", ""),
            "keyword": self.request.GET.get("q", ""),
        }

    def _get_base_queryset(self) -> QuerySet[Task]:
        queryset = (
            get_active_tasks(self.target_user, all_tasks=True)
            .select_related("user", "organization", "content_type")
            .annotate(
                task_type=Case(
                    When(type=Task.ERROR_FREQUENCY, then=Value(Task.ERROR)),
                    When(type=Task.ERROR_DISTRIBUTION, then=Value(Task.ERROR)),
                    When(type=Task.ERROR_GEOPORTAL, then=Value(Task.ERROR)),
                    default=F("type"),
                    output_field=CharField(),
                )
            )
        )

        if keyword := self.filter_params["keyword"]:
            queryset = queryset.annotate(user_name=Concat("user__first_name", Value(" "), "user__last_name")).filter(
                Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(organization__title__icontains=keyword)
                | Q(user_name__icontains=keyword)
            )

        return queryset

    def _apply_status_filter(self, queryset: QuerySet[Task]) -> QuerySet[Task]:
        if status := self.filter_params["status"]:
            return queryset.filter(status=status)
        return queryset

    def _apply_type_filter(self, queryset: QuerySet[Task]) -> QuerySet[Task]:
        if type_value := self.filter_params["type"]:
            return queryset.filter(task_type=type_value)
        return queryset

    def get_queryset(self) -> QuerySet[Task]:
        queryset = self._get_base_queryset()

        if self.filter_params["owner"] == "user":
            queryset = queryset.filter(user__pk=self.target_user.pk)

        queryset = self._apply_status_filter(queryset)
        queryset = self._apply_type_filter(queryset)

        return queryset.order_by("due_date")

    def _calculate_filter_counts(self) -> dict[str, int]:
        base_queryset = self._get_base_queryset()

        status_queryset = self._apply_type_filter(base_queryset)
        owner_status_counts = status_queryset.aggregate(
            user_tasks_count=Count("id", filter=Q(user__pk=self.target_user.pk)),
            all_tasks_count=Count("id"),
            **{f"status_{value}_count": Count("id", filter=Q(status=value)) for value in Task.FILTER_STATUSES},
        )

        type_queryset = self._apply_status_filter(base_queryset)
        type_counts = type_queryset.aggregate(
            **{f"type_{value}_count": Count("id", filter=Q(task_type=value)) for value in Task.FILTER_TYPES},
        )

        return {**owner_status_counts, **type_counts}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        params = self.filter_params
        counts = self._calculate_filter_counts()

        context["parent_links"] = {reverse("home"): _("Pradžia")}
        context["filters"] = [
            self._build_owner_filter(params, counts),
            self._build_status_filter(params, counts),
            self._build_type_filter(params, counts),
        ]
        context["search_url"] = reverse("user-task-list", args=[self.target_user.pk])
        context["search_query"] = dict(self.request.GET.copy())
        context["q"] = params["keyword"]

        return context

    def _build_owner_filter(self, params: dict[str, str], counts: dict[str, int]) -> dict[str, Any]:
        selected_owner = params["owner"]
        return {
            "title": _("Vykdytojas"),
            "items": [
                {
                    "title": _("Mano užduotys"),
                    "url": get_filter_url(self.request, "owner", "user", selected_owner == "user", facet_field=False),
                    "count": counts["user_tasks_count"],
                    "selected": selected_owner == "user",
                    "always_show": True,
                },
                {
                    "title": _("Visos užduotys"),
                    "url": get_filter_url(self.request, "owner", "all", selected_owner == "all", facet_field=False),
                    "count": counts["all_tasks_count"],
                    "selected": selected_owner == "all",
                    "always_show": True,
                },
            ],
        }

    def _build_status_filter(self, params: dict[str, str], counts: dict[str, int]) -> dict[str, Any]:
        selected_status = params["status"]
        return {
            "title": _("Būsena"),
            "items": [
                {
                    "title": title,
                    "url": get_filter_url(self.request, "status", value, selected_status == value, facet_field=False),
                    "count": counts.get(f"status_{value}_count", 0),
                    "selected": selected_status == value,
                }
                for value, title in Task.FILTER_STATUSES.items()
            ],
        }

    def _build_type_filter(self, params: dict[str, str], counts: dict[str, int]) -> dict[str, Any]:
        selected_type = params["type"]
        return {
            "title": _("Tipas"),
            "items": [
                {
                    "title": title,
                    "url": get_filter_url(self.request, "type", value, selected_type == value, facet_field=False),
                    "count": counts.get(f"type_{value}_count", 0),
                    "selected": selected_type == value,
                }
                for value, title in Task.FILTER_TYPES.items()
            ],
        }


class TaskView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "vitrina/tasks/detail.html"
    pk_url_kwarg = "task_id"

    @staticmethod
    def _can_view_task(user: User, task: Task) -> bool:
        if user.is_staff or user.is_superuser:
            return True
        return get_active_tasks(user, all_tasks=True).filter(pk=task.pk).exists()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        self.object = get_object_or_404(Task, pk=kwargs.get("task_id"))

        if not self._can_view_task(request.user, self.object):
            raise PermissionDenied("You don't have permission to view this task")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        task = self.object

        context["org"] = (
            Organization.objects.filter(pk=task.organization_id).values_list("title", flat=True).first()
            if task.organization_id
            else None
        )
        context["object_url"] = task.content_object.get_absolute_url if task.content_object else None
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("user-task-list", args=[self.request.user.pk]): _("Užduotys"),
        }

        return context


class BaseTaskActionView(LoginRequiredMixin, PermissionRequiredMixin):
    task: Task

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.task = get_object_or_404(Task, pk=kwargs.get("task_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self) -> bool:
        if not self.request.user.is_authenticated:
            return False

        user_tasks = get_active_tasks(self.request.user, all_tasks=True)
        return user_tasks.filter(pk=self.task.pk).exists() and self.task.status != Task.COMPLETED

    def get_success_url(self) -> str:
        return reverse("user-task-list", kwargs={"pk": self.request.user.pk})


class CloseTaskView(BaseTaskActionView, DeleteView):
    model = Task
    template_name = "confirm_close.html"
    pk_url_kwarg = "task_id"

    @property
    def object(self) -> Task:
        return self.task

    @object.setter
    def object(self, value: Task) -> None:
        self.task = value

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Užduoties uždarymas")
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        self.task.status = Task.COMPLETED
        self.task.completed = datetime.datetime.now()
        self.task.save(update_fields=["status", "completed"])
        return HttpResponseRedirect(self.get_success_url())


class AssignTaskView(BaseTaskActionView, TemplateView):
    template_name = "confirm_reassign.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["task"] = self.task
        context["current_title"] = _("Užduoties priskyrimas")
        return context

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.task.user = request.user
        self.task.status = Task.ASSIGNED
        self.task.assigned = datetime.datetime.now()
        self.task.save(update_fields=["user", "status", "assigned"])
        return redirect(self.get_success_url())
