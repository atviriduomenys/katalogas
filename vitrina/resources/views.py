from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
from django.forms import BaseForm
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView
from parler.views import TranslatableCreateView, TranslatableUpdateView
from reversion import add_to_revision

from vitrina import settings
from vitrina.comments.models import Comment
from vitrina.datasets.models import Dataset
from vitrina.datasets.services import DynamicResourceService
from vitrina.orgs.models import Representative
from vitrina.orgs.services import Action, has_perm
from vitrina.plans.models import Plan
from vitrina.requests.models import Request
from vitrina.resources.forms import DatasetResourceForm
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import Version
from vitrina.structure.views import DatasetStructureMixin, ModelCreateView
from vitrina.views import HistoryMixin


class ResourceDetailView(PermissionRequiredMixin, HistoryMixin, DatasetStructureMixin, DetailView):
    template_name = "vitrina/resources/detail.html"
    model = DatasetDistribution
    pk_url_kwarg = "resource_id"

    detail_url_name = "resource-detail"
    history_url_name = "dataset-history"

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs["pk"])
        return has_perm(self.request.user, Action.VIEW, dataset)

    def get_history_object(self):
        return self.object.dataset

    def get_detail_url(self):
        return self.object.dataset.get_absolute_url()

    def get_child_resources_url(self) -> str:
        return reverse(
            "dataset-child-resources",
            args=[self.object.dataset.pk],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resource"] = self.object
        context["dataset"] = self.object.dataset
        context["can_update"] = has_perm(self.request.user, Action.UPDATE, self.object)
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object.dataset,
        )
        # TODO: use spinta POST /:inspect to fetch manifest after #477 is done
        # TODO: do not change to True until inspect is finished and html is correct
        context["structure_acceptable"] = False
        context["params"] = self.object.params.all().order_by("name")
        context["models"] = self.object.model_set.all()
        context["is_disabled"] = (
            self.object.metadata_version is not None and not self.object.metadata_version.is_draft()
        )
        return context


class ResourceCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TranslatableCreateView,
):
    model = DatasetDistribution
    template_name = "vitrina/resources/form.html"
    context_object_name = "datasetdistribution"
    form_class = DatasetResourceForm

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, DatasetDistribution, self.dataset)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            return redirect(self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Naujas duomenų rinkinio šaltinis")
        return context

    def get(self, request, *args, **kwargs):
        return super(ResourceCreateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        resource: DatasetDistribution = form.save(commit=False)
        resource.dataset = self.dataset
        resource.save()

        name = form.cleaned_data.get("name")
        if not name:
            latest_name = (
                DatasetDistribution.objects.filter(
                    dataset=self.dataset,
                    name__iregex=r"resource[0-9]+",
                )
                .order_by("name")
                .values_list("name", flat=True)
                .last()
            )
            if not latest_name:
                name = "resource1"
            else:
                duplicate_name_suffix = latest_name.replace("resource", "")
                try:
                    duplicate_name_suffix = int(duplicate_name_suffix)
                except ValueError:
                    duplicate_name_suffix = 0
                duplicate_name_suffix += 1
                name = f"resource{duplicate_name_suffix}"
        resource.name = name

        if not self.dataset.datasetdistribution_set.exclude(pk=resource.pk).exists():
            dataset_plans = Plan.objects.filter(plandataset__dataset=self.dataset)
            for plan in dataset_plans:
                if (
                    plan.planrequest_set.filter(request__status=Request.OPENED).count() == plan.planrequest_set.count()
                    and plan.plandataset_set.annotate(
                        has_distributions=Exists(
                            DatasetDistribution.objects.filter(
                                dataset_id=OuterRef("dataset_id"),
                            )
                        )
                    ).count()
                    == plan.plandataset_set.count()
                ):
                    plan.is_closed = True
                    plan.save()

        if self.dataset.status != Dataset.HAS_DATA and self.dataset.is_public:
            Comment.objects.create(
                content_type=ContentType.objects.get_for_model(self.dataset),
                object_id=self.dataset.pk,
                type=Comment.STATUS,
                status=Comment.OPENED,
                user=self.request.user,
            )
            self.dataset.status = Dataset.HAS_DATA
            self.dataset.save()

        if applicable_legislation_urls := form.cleaned_data.get("applicable_legislation"):
            resource.update_applicable_legislation(applicable_legislation_urls)

        resource.save()
        return redirect(resource.get_absolute_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        return kwargs


class ResourceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TranslatableUpdateView):
    model = DatasetDistribution
    template_name = "vitrina/resources/form.html"
    context_object_name = "datasetdistribution"
    form_class = DatasetResourceForm

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(DatasetDistribution, pk=kwargs["pk"])
        if not self.has_permission():
            return self.handle_no_permission()
        self.metadata_version = None
        version_id = kwargs.get("version_id")
        if version_id is not None:
            self.metadata_version = get_object_or_404(
                Version,
                pk=version_id,
            )
            if not self.metadata_version.is_draft():
                messages.error(request, _("Negalima redaguoti šaltinio, kai versijos būsena nėra juodraštis."))
                return redirect(self.resource.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.resource)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            return redirect(self.resource.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Duomenų rinkinio šaltinio redagavimas")
        return context

    def get(self, request, *args, **kwargs):
        return super(ResourceUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        applicable_legislation_urls = form.cleaned_data.pop("applicable_legislation")
        resource: DatasetDistribution = form.save()
        name = form.cleaned_data.get("name")

        if metadata := resource.metadata.first():
            metadata.name = name
            metadata.access = form.cleaned_data.get("access") or None
            metadata.title = form.cleaned_data.get("title")
            metadata.description = form.cleaned_data.get("description")
            metadata.level_given = form.cleaned_data.get("level")
            metadata.version += 1
            metadata.save()

        if "applicable_legislation" in form.changed_data:
            resource.update_applicable_legislation(applicable_legislation_urls)

        resource.save()
        return redirect(resource.get_absolute_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        resource = get_object_or_404(DatasetDistribution, id=self.kwargs["pk"])
        kwargs["dataset"] = resource.dataset
        return kwargs


class ResourceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = DatasetDistribution

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(DatasetDistribution, pk=kwargs["pk"])
        if not self.has_permission():
            return self.handle_no_permission()
        self.metadata_version = None
        version_id = kwargs.get("version_id")
        if version_id is not None:
            self.metadata_version = get_object_or_404(
                Version,
                pk=version_id,
            )
            if not self.metadata_version.is_draft():
                messages.error(request, _("Negalima trinti šaltinio, kai versijos būsena nėra juodraštis."))
                return redirect(self.resource.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.DELETE, self.resource)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            if self.resource.metadata_version:
                url = reverse("dataset-detail", kwargs={"pk": self.resource.dataset.pk})
                return HttpResponseRedirect(f"{url}?resource_version={self.resource.metadata_version.pk}")
            return redirect(self.resource.dataset)

    def form_valid(self, form: BaseForm) -> HttpResponse:
        resource = get_object_or_404(DatasetDistribution, id=self.kwargs["pk"])
        dataset = get_object_or_404(Dataset, id=resource.dataset_id)
        add_to_revision(resource)
        resource.delete()
        resource.metadata.all().delete()

        if not DatasetDistribution.objects.filter(dataset=dataset).exists() and dataset.is_public:
            if dataset.plandataset_set.exists():
                dataset.status = Dataset.PLANNED
                comment_status = Comment.PLANNED
            else:
                dataset.status = Dataset.INVENTORED
                comment_status = Comment.INVENTORED

            Comment.objects.create(
                content_type=ContentType.objects.get_for_model(dataset),
                object_id=dataset.pk,
                type=Comment.STATUS,
                status=comment_status,
                user=self.request.user,
            )
            dataset.save()

        if version_id := self.kwargs.get("version_id"):
            url = reverse("dataset-detail", kwargs={"pk": dataset.pk})
            return HttpResponseRedirect(f"{url}?resource_version={version_id}")

        return redirect(dataset)


class ResourceModelCreateView(ModelCreateView):
    resource: DatasetDistribution

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(DatasetDistribution, pk=kwargs.get("resource_id"))
        self.metadata_version = get_object_or_404(Version, pk=kwargs.get("version_id"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Modelio pridėjimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            reverse(
                "resource-detail", args=[self.dataset.pk, self.metadata_version.pk, self.resource.pk]
            ): self.resource.title,
        }
        return context

    def form_valid(self, form):
        super().form_valid(form)
        model = self.object.object
        model.distribution = self.resource
        model.metadata_version = self.metadata_version
        model.save()
        return redirect(self.resource.get_absolute_url())


class DynamicResourceDetailView(PermissionRequiredMixin, HistoryMixin, DatasetStructureMixin, DetailView):
    template_name = "vitrina/resources/dynamic_detail.html"

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs["pk"])
        return has_perm(self.request.user, Action.VIEW, dataset)

    def get_data(
        self, dataset_pk: int, metadata_version_pk: int | None, model_name: str, distribution_format: str
    ) -> dict:
        dataset = get_object_or_404(Dataset, id=dataset_pk)
        metadata_version = None
        if metadata_version_pk:
            metadata_version = get_object_or_404(Version, id=metadata_version_pk)

        dynamic_resource = DynamicResourceService(dataset, metadata_version)
        data = dynamic_resource.retrieve_data(dataset_pk, metadata_version, model_name, distribution_format)
        if not data:
            raise Http404("Data not found")
        return data

    def get_detail_url(self):
        return self.dataset.get_absolute_url()

    def get(self, request, *args, **kwargs):
        dataset_pk = self.kwargs.get("pk")
        metadata_version_pk = self.kwargs.get("version_id")
        distribution_name = self.kwargs.get("distribution_name")
        distribution_format = self.kwargs.get("format").upper()
        dynamic_resource = self.get_data(dataset_pk, metadata_version_pk, distribution_name, distribution_format)

        self.dataset = get_object_or_404(Dataset, id=dataset_pk)
        self.object = self.dataset
        self.models = dynamic_resource["models"]

        name_for_urls = self.models[0].name if self.models else None

        context = {
            "resource": dynamic_resource,
            "dataset": self.dataset,
            "format": distribution_format,
            "detail_url": self.get_detail_url(),
            "child_resources_url": self.get_child_resources_url(),
            "structure_url": reverse("dataset-structure", args=[self.dataset.pk, metadata_version_pk]),
            "data_url": reverse("model-data", args=[self.dataset.pk, metadata_version_pk, name_for_urls])
            if name_for_urls
            else None,
            "api_url": reverse("getall-api", args=[self.dataset.pk, metadata_version_pk, name_for_urls])
            if name_for_urls
            else None,
            "can_view_members": has_perm(
                self.request.user,
                Action.VIEW,
                Representative,
                self.dataset,
            ),
            "can_manage_history": has_perm(
                self.request.user,
                Action.HISTORY_VIEW,
                self.dataset,
            ),
            "history_url": reverse("dataset-history", args=[self.dataset.pk]),
        }
        return render(request, self.template_name, context)
