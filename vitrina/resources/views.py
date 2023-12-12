import uuid

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from vitrina import settings
from vitrina.comments.models import Comment
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Representative
from vitrina.orgs.services import Action, has_perm
from vitrina.plans.models import Plan
from vitrina.requests.models import Request
from vitrina.resources.forms import DatasetResourceForm
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import Metadata
from vitrina.structure.views import DatasetStructureMixin, ModelCreateView
from vitrina.views import HistoryMixin


class ResourceDetailView(
    HistoryMixin,
    DatasetStructureMixin,
    DetailView
):
    template_name = 'vitrina/resources/detail.html'
    model = DatasetDistribution
    pk_url_kwarg = 'resource_id'

    detail_url_name = "resource-detail"
    history_url_name = "dataset-history"

    def get_history_object(self):
        return self.object.dataset

    def get_detail_url(self):
        return self.object.dataset.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['resource'] = self.object
        context['dataset'] = self.object.dataset
        context['can_update'] = has_perm(self.request.user, Action.UPDATE, self.object)
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object.dataset,
        )
        # TODO: use spinta POST /:inspect to fetch manifest
        context['structure_acceptable'] = True
        context['params'] = self.object.params.all().order_by('name')
        context['models'] = self.object.model_set.all()
        return context


class ResourceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = DatasetDistribution
    template_name = 'vitrina/resources/form.html'
    context_object_name = 'datasetdistribution'
    form_class = DatasetResourceForm

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
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
        context['current_title'] = _('Naujas duomenų rinkinio šaltinis')
        return context

    def get(self, request, *args, **kwargs):
        return super(ResourceCreateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        resource = form.save(commit=False)
        resource.dataset = self.dataset
        if resource.download_url:
            resource.type = 'URL'
        resource.save()

        name = form.cleaned_data.get('name')
        if not name:
            name = Metadata.objects.filter(
                dataset=self.dataset,
                content_type=ContentType.objects.get_for_model(DatasetDistribution),
                name__iregex=r"resource[0-9]+"
            ).order_by('name').values_list('name', flat=True).last()
            if not name:
                name = 'resource1'
            else:
                n = name.replace('resource', '')
                try:
                    n = int(n)
                except ValueError:
                    n = 0
                n += 1
                name = f"resource{n}"
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.dataset,
            content_type=ContentType.objects.get_for_model(resource),
            object_id=resource.pk,
            name=name,
            prepare_ast={},
            access=form.cleaned_data.get('access') or None,
            version=1,
        )

        if not self.dataset.datasetdistribution_set.exclude(pk=resource.pk).exists():
            dataset_plans = Plan.objects.filter(plandataset__dataset=self.dataset)
            for plan in dataset_plans:
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

        if self.dataset.status != Dataset.HAS_DATA and self.dataset.is_public:
            Comment.objects.create(content_type=ContentType.objects.get_for_model(self.dataset),
                                   object_id=self.dataset.pk,
                                   type=Comment.STATUS,
                                   status=Comment.OPENED,
                                   user=self.request.user)
            self.dataset.status = Dataset.HAS_DATA
            self.dataset.save()

        return redirect(resource.get_absolute_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs


class ResourceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = DatasetDistribution
    template_name = 'vitrina/resources/form.html'
    context_object_name = 'datasetdistribution'
    form_class = DatasetResourceForm

    def has_permission(self):
        resource = get_object_or_404(DatasetDistribution, id=self.kwargs['pk'])
        return has_perm(self.request.user, Action.UPDATE, resource)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            resource = get_object_or_404(DatasetDistribution, id=self.kwargs['pk'])
            return redirect(resource.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Duomenų rinkinio šaltinio redagavimas')
        return context

    def get(self, request, *args, **kwargs):
        return super(ResourceUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        resource = form.save()
        name = form.cleaned_data.get('name')
        if not name:
            name = Metadata.objects.filter(
                dataset=resource.dataset,
                content_type=ContentType.objects.get_for_model(DatasetDistribution),
                name__iregex=r"resource[0-9]+"
            ).order_by('name').values_list('name', flat=True).last()
            if not name:
                name = 'resource1'
            else:
                n = name.replace('resource', '')
                try:
                    n = int(n)
                except ValueError:
                    n = 0
                n += 1
                name = f"resource{n}"
        if metadata := resource.metadata.first():
            metadata.name = name
            metadata.access = form.cleaned_data.get('access') or None
            metadata.version += 1
            metadata.save()
        else:
            Metadata.objects.create(
                uuid=str(uuid.uuid4()),
                dataset=resource.dataset,
                content_type=ContentType.objects.get_for_model(resource),
                object_id=resource.pk,
                name=name,
                prepare_ast={},
                access=form.cleaned_data.get('access') or None,
                version=1,
            )
        return redirect(resource.get_absolute_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        resource = get_object_or_404(DatasetDistribution, id=self.kwargs['pk'])
        kwargs['dataset'] = resource.dataset
        return kwargs


class ResourceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = DatasetDistribution

    def has_permission(self):
        resource = get_object_or_404(DatasetDistribution, id=self.kwargs['pk'])
        return has_perm(self.request.user, Action.DELETE, resource)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            resource = get_object_or_404(DatasetDistribution, id=self.kwargs['pk'])
            return redirect(resource.dataset)

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        resource = get_object_or_404(DatasetDistribution, id=self.kwargs['pk'])
        dataset = get_object_or_404(Dataset, id=resource.dataset_id)
        resource.delete()

        if not DatasetDistribution.objects.filter(dataset=dataset) and dataset.is_public:
            if dataset.plandataset_set.exists():
                dataset.status = Dataset.PLANNED
                comment_status = Comment.PLANNED
            else:
                dataset.status = Dataset.INVENTORED
                comment_status = Comment.INVENTORED

            Comment.objects.create(content_type=ContentType.objects.get_for_model(dataset),
                                   object_id=dataset.pk,
                                   type=Comment.STATUS,
                                   status=comment_status,
                                   user=self.request.user)
            dataset.save()
        return redirect(dataset)


class ResourceModelCreateView(ModelCreateView):
    resource: DatasetDistribution

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(DatasetDistribution, pk=kwargs.get('resource_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Modelio pridėjimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('resource-detail', args=[self.dataset.pk, self.resource.pk]): self.resource.title,
        }
        return context

    def form_valid(self, form):
        super().form_valid(form)
        model = self.object.object
        model.distribution = self.resource
        model.save()
        return redirect(self.resource.get_absolute_url())
