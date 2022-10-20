from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, DeleteView

from vitrina import settings
from vitrina.datasets.models import Dataset
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.forms import DatasetResourceForm
from vitrina.resources.models import DatasetDistribution
from django.utils.translation import gettext_lazy as _


class ResourceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = DatasetDistribution
    template_name = 'base_form.html'
    context_object_name = 'datasetdistribution'
    form_class = DatasetResourceForm

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, DatasetDistribution)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
            return redirect(dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Naujas duomenų rinkinio šaltinis')
        return context

    def get(self, request, *args, **kwargs):
        return super(ResourceCreateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        resource = form.save(commit=False)
        dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
        resource.dataset = dataset
        if resource.download_url:
            resource.type = 'URL'
        resource.save()
        return redirect(resource.dataset)


class ResourceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = DatasetDistribution
    template_name = 'base_form.html'
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
        return redirect(resource.dataset)


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
        return redirect(dataset)
