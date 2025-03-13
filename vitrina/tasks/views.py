import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Case, When, Value, CharField, F, Q
from django.db.models.functions import Concat
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, DeleteView, TemplateView, ListView
from django.utils.translation import gettext_lazy as _

from vitrina.helpers import get_filter_url
from vitrina.orgs.models import Organization
from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "vitrina/tasks/list.html"
    paginate_by = 20

    def get_queryset(self, filter_owner=True):
        queryset = super().get_queryset()
        queryset = get_active_tasks(self.request.user, queryset, all_tasks=True)

        owner_selected_value = self.request.GET.get("owner", "all")
        status_selected_value = self.request.GET.get("status", "")
        type_selected_value = self.request.GET.get("type", "")
        keyword = self.request.GET.get("q", "")

        if filter_owner and owner_selected_value == "user":
            queryset = queryset.filter(user__pk=self.request.user.pk)
        if status_selected_value:
            queryset = queryset.filter(status=status_selected_value)
        if type_selected_value:
            queryset = queryset.annotate(
                task_type=Case(
                    When(type=Task.ERROR_FREQUENCY, then=Value(Task.ERROR)),
                    When(type=Task.ERROR_DISTRIBUTION, then=Value(Task.ERROR)),
                    When(type=Task.ERROR_GEOPORTAL, then=Value(Task.ERROR)),
                    default=F("type"),
                    output_field=CharField(),
                )
            ).filter(task_type=type_selected_value)
        if keyword:
            queryset = queryset.annotate(
                user_name=Concat("user__first_name", Value(" "), "user__last_name")
            ).filter(
                Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(organization__title__icontains=keyword)
                | Q(user_name__icontains=keyword)
            )

        return queryset.order_by("due_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
        }

        owner_selected_value = self.request.GET.get("owner", "all")
        status_selected_value = self.request.GET.get("status", "")
        type_selected_value = self.request.GET.get("type", "")
        keyword = self.request.GET.get("q", "")
        queryset = self.get_queryset()

        context["filters"] = [
            {
                "title": _("Vykdytojas"),
                "items": [
                    {
                        "title": _("Mano užduotys"),
                        "url": get_filter_url(
                            self.request,
                            "owner",
                            "user",
                            owner_selected_value == "user",
                            facet_field=False,
                        ),
                        "count": queryset.filter(user__pk=self.request.user.pk).count(),
                        "selected": owner_selected_value == "user",
                        "always_show": True,
                    },
                    {
                        "title": _("Visos užduotys"),
                        "url": get_filter_url(
                            self.request,
                            "owner",
                            "all",
                            owner_selected_value == "all",
                            facet_field=False,
                        ),
                        "count": self.get_queryset(filter_owner=False).count(),
                        "selected": owner_selected_value == "all",
                        "always_show": True,
                    },
                ],
            },
            {
                "title": _("Būsena"),
                "items": [
                    {
                        "title": title,
                        "url": get_filter_url(
                            self.request,
                            "status",
                            value,
                            status_selected_value == value,
                            facet_field=False,
                        ),
                        "count": queryset.filter(status=value).count(),
                        "selected": status_selected_value == value,
                    }
                    for value, title in Task.FILTER_STATUSES.items()
                ],
            },
            {
                "title": _("Tipas"),
                "items": [
                    {
                        "title": title,
                        "url": get_filter_url(
                            self.request,
                            "type",
                            value,
                            type_selected_value == value,
                            facet_field=False,
                        ),
                        "count": queryset.annotate(
                            task_type=Case(
                                When(type=Task.ERROR_FREQUENCY, then=Value(Task.ERROR)),
                                When(
                                    type=Task.ERROR_DISTRIBUTION, then=Value(Task.ERROR)
                                ),
                                When(type=Task.ERROR_GEOPORTAL, then=Value(Task.ERROR)),
                                default=F("type"),
                                output_field=CharField(),
                            )
                        )
                        .filter(task_type=value)
                        .count(),
                        "selected": type_selected_value == value,
                    }
                    for value, title in Task.FILTER_TYPES.items()
                ],
            },
        ]
        context["search_url"] = reverse("user-task-list", args=[self.request.user.pk])
        context["search_query"] = dict(self.request.GET.copy())
        context["q"] = keyword
        return context


class TaskView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = "vitrina/tasks/detail.html"
    pk_url_kwarg = "task_id"

    task: Task

    def dispatch(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=kwargs.get("task_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            user_tasks = get_active_tasks(self.request.user, all_tasks=True)
            if user_tasks.filter(pk=self.task.pk):
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        org = ""
        object_url = None
        if task.organization_id is not None:
            org = (
                Organization.objects.filter(pk=task.organization_id)
                .values_list("title", flat=True)
                .first()
            )
        if task.content_object:
            object_url = task.content_object.get_absolute_url
        context["org"] = org
        context["object_url"] = object_url
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("user-task-list", args=[self.request.user.pk]): _("Užduotys"),
        }
        context["has_perm"] = self.has_permission()
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
            if (
                user_tasks.filter(pk=self.object.pk)
                and self.object.status != Task.COMPLETED
            ):
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Užduoties uždarymas")
        return context

    def delete(self, request, *args, **kwargs):
        self.object.status = Task.COMPLETED
        self.object.completed = datetime.datetime.now()
        self.object.save()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

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
            if (
                user_tasks.filter(pk=self.task.pk)
                and self.task.status != Task.COMPLETED
            ):
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = self.task
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
