from typing import Type, Any
from importlib.metadata import version, PackageNotFoundError
import json

from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.db.models import Model, QuerySet, Prefetch
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms import BaseFormSet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from django.db.models import Count
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.views.generic.edit import ProcessFormView

from reversion.models import Version, Revision

from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset
from vitrina.projects.services import get_projects
from vitrina.requests.models import Request
from vitrina.orgs.models import Organization, Representative
from vitrina.statistics.models import StatRoute
from vitrina.users.models import User
from vitrina.orgs.services import has_perm, Action
from vitrina.utils import RevisionComment


def home(request):
    cards_limit = 3
    coordinator_count = (
        User.objects.select_related("representative")
        .filter(representative__role__in=Representative.COORDINATOR_ROLES)
        .distinct("representative__user")
        .count()
    )
    manager_count = (
        User.objects.select_related("representative")
        .filter(representative__role__in=Representative.MANAGER_ROLES)
        .exclude(representative__role__in=Representative.COORDINATOR_ROLES)
        .distinct("representative__user")
        .count()
    )
    user_count = User.objects.exclude(
        representative__role__in=Representative.COORDINATOR_ROLES + Representative.MANAGER_ROLES
    ).count()

    return render(
        request,
        "landing.html",
        {
            "counts": {
                "dataset": Dataset.restricted.for_user(request.user).count(),
                "organization": Organization.public.count(),
                "project": get_projects(request.user).count(),
                "coordinators": coordinator_count,
                "managers": manager_count,
                "users": user_count,
            },
            "categories": (Category.objects.filter(featured=True).order_by("title")),
            "datasets": (
                Dataset.restricted.for_user(request.user)
                .select_related("organization")
                .order_by("-published")[:cards_limit]
            ),
            "requests": Request.public.prefetch_related("organizations").order_by("-created")[:cards_limit],
            "projects": get_projects(request.user, limit=cards_limit, require_images=True),
            "orgs": (
                Organization.public.filter(
                    numchild=0,
                    image__isnull=False,
                )
                .annotate(datasets=Count("dataset"))
                .order_by("-datasets")[:cards_limit]
            ),
            "stat_routes": (StatRoute.objects.filter(featured=True).order_by("order")),
        },
    )


class PlanMixin:
    object: Model
    plan_url_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "plan_url_name": self.get_plan_url_name(),
                "plan_url": self.get_plan_url(),
            }
        )
        return context

    def get_plan_url_name(self):
        return self.plan_url_name

    def get_plan_url(self):
        obj = self.get_plan_object()
        url_name = self.get_plan_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_plan_object(self):
        return self.object


class HistoryView(PermissionRequiredMixin, TemplateView):
    template_name = "history.html"
    model: Type[Model] = None
    detail_url_name = None
    history_url_name = None
    tabs_template_name: str
    paginate_by = 20

    object: Model

    def dispatch(self, request, *args, **kwargs):
        object_id = self.kwargs.get("pk")
        self.object = get_object_or_404(self.model, pk=object_id)
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.HISTORY_VIEW, self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(self.get_revisions(), self.paginate_by)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        context.update(
            {
                "detail_url_name": self.get_detail_url_name(),
                "history_url_name": self.get_history_url_name(),
                "detail_url": self.get_detail_url(),
                "child_resources_url": self.get_child_resources_url(),
                "history_url": self.get_history_url(),
                "history": self.get_history_list(page_obj.object_list),
                "can_manage_history": has_perm(
                    self.request.user,
                    Action.HISTORY_VIEW,
                    self.get_history_object(),
                ),
                "tabs_template_name": self.tabs_template_name,
                "page_obj": page_obj,
            }
        )

        return context

    def get_history_list(self, revisions: QuerySet[Revision]) -> list[dict[str, Any]]:
        history = []

        for revision in revisions:
            entry = {
                "date": revision.date_created,
                "user": revision.user,
                "action": {
                    "comment": self.prep_comment_for_display(revision.comment),
                    "objects": self.prep_versions_for_display(revision.version_set.all()),
                },
            }
            history.append(entry)
        return history

    def prep_versions_for_display(self, versions: QuerySet[Version]) -> list[tuple[str, str | None]]:
        objects = []
        for version_obj in versions:
            url = None

            if (object := version_obj.object) and hasattr(object, "get_absolute_url"):
                url = object.get_absolute_url()

            objects.append((version_obj.object_repr, url))
        return objects

    def prep_comment_for_display(self, comment: str) -> str:
        try:
            revision_comment = RevisionComment.from_json(comment)
            return f"{revision_comment.action}({revision_comment.kwargs})"
        except (json.JSONDecodeError, ValueError, TypeError):
            return (
                self.model.HISTORY_MESSAGES.get(comment)
                if (hasattr(self.model, "HISTORY_MESSAGES") and self.model.HISTORY_MESSAGES.get(comment))
                else comment
            )

    def get_revisions(self) -> QuerySet[Revision]:
        versions = self.get_history_objects()
        return (
            Revision.objects.filter(version__in=self.get_history_objects())
            .distinct()
            .order_by("-date_created")
            .prefetch_related(Prefetch("version_set", queryset=versions))
        )

    def get_detail_url_name(self):
        return self.detail_url_name

    def get_history_url_name(self):
        return self.history_url_name

    def get_child_resources_url(self):
        obj = self.get_detail_object()
        return reverse("dataset-child-resources", args=[obj.pk])

    def get_detail_url(self):
        obj = self.get_detail_object()
        url_name = self.get_detail_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_history_url(self):
        obj = self.get_history_object()
        url_name = self.get_history_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_history_object(self):
        return self.object

    def get_detail_object(self):
        return self.object

    def get_history_objects(self) -> QuerySet[Version]:
        return Version.objects.get_for_object(self.get_history_object())


class HistoryMixin:
    detail_url_name = None
    history_url_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "detail_url_name": self.get_detail_url_name(),
                "history_url_name": self.get_history_url_name(),
                "detail_url": self.get_detail_url(),
                "child_resources_url": self.get_child_resources_url(),
                "history_url": self.get_history_url(),
                "can_manage_history": has_perm(
                    self.request.user,
                    Action.HISTORY_VIEW,
                    self.get_history_object(),
                ),
            }
        )
        return context

    def get_detail_url_name(self):
        return self.detail_url_name

    def get_history_url_name(self):
        return self.history_url_name

    def get_detail_url(self):
        obj = self.get_detail_object()
        url_name = self.get_detail_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_child_resources_url(self):
        obj = self.get_detail_object()
        return reverse("dataset-child-resources", args=[obj.pk])

    def get_history_url(self):
        obj = self.get_history_object()
        if hasattr(self, "metadata_version") and self.metadata_version:
            return reverse(
                "dataset-structure-history",
                kwargs={"pk": obj.pk, "version_id": self.metadata_version.pk},
            )
        else:
            return reverse(
                "dataset-structure-history-no-version",
                kwargs={
                    "pk": obj.pk,
                },
            )

    def get_history_object(self):
        return self.object

    def get_detail_object(self):
        return self.object


class ChartMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class FormsetView(TemplateResponseMixin, ContextMixin, ProcessFormView):
    success_url = None

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

    def get_formset_kwargs(self) -> dict:
        formset_kwargs = {}
        if self.request.method in ("POST", "PUT"):
            formset_kwargs = {"data": self.request.POST, "files": self.request.FILES}

        return formset_kwargs

    def get_formset(self) -> BaseFormSet:
        raise ImproperlyConfigured("get_formset method must be implemented")

    def get_context_data(self, **kwargs):
        if "formset" not in kwargs:
            kwargs["formset"] = self.get_formset()
        return super().get_context_data(**kwargs)

    def get_success_url(self) -> str:
        if not self.success_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return str(self.success_url)

    def formset_valid(self, formset: BaseFormSet) -> HttpResponse:
        return HttpResponseRedirect(self.get_success_url())

    def formset_invalid(self, formset: BaseFormSet) -> HttpResponse:
        return self.render_to_response(self.get_context_data(formset=formset))

    def post(self, request, *args, **kwargs) -> HttpResponse:
        formset = self.get_formset()
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset)


def version_view(request):
    try:
        app_version = version("vitrina")
    except PackageNotFoundError:
        app_version = "unknown"

    return JsonResponse({"version": app_version})
