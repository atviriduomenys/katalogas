from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views.generic.edit import DeleteView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.datasets.models import Dataset
from vitrina.messages.helpers import prepare_email_by_identifier_for_sub
from vitrina.messages.models import Subscription
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.forms import ProjectForm
from vitrina.projects.models import Project
from vitrina.tasks.models import Task
from vitrina.views import HistoryMixin, HistoryView
from vitrina.helpers import prepare_email_by_identifier, send_email_with_logging


class ProjectListView(ListView):
    model = Project
    queryset = Project.public.all()
    template_name = 'vitrina/projects/list.html'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.has_update_perm = has_perm(
            request.user,
            Action.UPDATE,
            Project,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.has_update_perm:
            if self.request.user.is_authenticated:
                qs = qs.filter(Q(status=Project.APPROVED) | Q(user=self.request.user))
            else:
                qs = qs.filter(status=Project.APPROVED)
        return qs.order_by('-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_see_status'] = self.has_update_perm
        return context


class ProjectDetailView(HistoryMixin, DetailView):
    model = Project
    template_name = 'vitrina/projects/detail.html'
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_update_project'] = has_perm(
            self.request.user,
            Action.UPDATE,
            self.object
        )
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('project-list'): _('Panaudojimo atvejai'),
        }
        return context


class ProjectCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    CreateView
):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Project)

    def form_valid(self, form):
        self.object = form.save(commit=True)
        self.object.user = self.request.user
        self.object.status = Project.CREATED
        self.object.save()
        set_comment(Project.CREATED)
        Task.objects.create(
            title=f"Užregistruotas naujas panaudos atvejis: {ContentType.objects.get_for_model(self.object)}, id: {self.object.pk}",
            description=f"Portale užregistruotas naujas panaudos atvejis.",
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.pk,
            status=Task.CREATED,
            user=self.request.user,
            type=Task.REQUEST
        )
        email_data = prepare_email_by_identifier('use-case-registered',
                                                 'Sveiki, portale užregistruotas naujas panaudos atvejis.',
                                                 'Užregistruotas naujas panaudos atvejis', [])
        if self.object.user is not None:
            if self.object.user.email is not None:
                send_email_with_logging(email_data, email_data)

        Subscription.objects.create(
            user=self.request.user,
            content_type=ContentType.objects.get_for_model(Project),
            object_id=self.object.pk,
            sub_type=Subscription.PROJECT,
            email_subscribed=True,
            project_update_sub=True,
            project_comments_sub=True,
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudos atvejo registracija')
        return context_data


class ProjectUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def has_permission(self):
        project = self.get_object()
        return has_perm(self.request.user, Action.UPDATE, project)

    def form_valid(self, form):
        super().form_valid(form)
        self.object = form.save(commit=True)
        self.object.save()
        set_comment(Project.EDITED)
        sub_ct = ContentType.objects.get_for_model(self.object)
        subs = Subscription.objects.filter(sub_type=Subscription.PROJECT,
                                           content_type=sub_ct,
                                           object_id=self.object.id,
                                           project_update_sub=True)
        if self.object.user is not None:
            subs = subs.exclude(user=self.object.user)
        email_data = prepare_email_by_identifier_for_sub('project-updated-sub',
                                                         'Sveiki, pranešame jums apie tai, kad,'
                                                         ' panaudos atvėjis {object} buvo atnaujintas.',
                                                         'Atnaujintas panaudos atvėjis', {'object': self.object.title})
        sub_email_list = []
        for sub in subs:
            Task.objects.create(
                title=f"Atnaujintas panaudos atvejis: {self.object}.",
                description=f"Šis panaudos atvėjis: {self.object}, buvo atnaujintas.",
                content_type=ContentType.objects.get_for_model(self.object),
                object_id=self.object.pk,
                status=Task.CREATED,
                type=Task.PROJECT,
                user=sub.user
            )
            if sub.user.email and sub.email_subscribed:
                if sub.user.organization:
                    orgs = [sub.user.organization] + list(sub.user.organization.get_descendants())
                    sub_email_list = [org.email for org in orgs]
                sub_email_list.append(sub.user.email)
        send_email_with_logging(email_data, sub_email_list)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudos atvejo redagavimas')
        return context_data


class ProjectHistoryView(HistoryView):
    model = Project
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'
    tabs_template_name = 'vitrina/projects/tabs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('project-list'): _('Panaudojimo atvejai'),
            reverse('project-detail', args=[self.object.pk]): self.object
        }
        return context


class ProjectDatasetsView(HistoryMixin, ListView):
    model = Dataset
    template_name = 'vitrina/projects/datasets.html'
    paginate_by = 20

    object: Project
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Dataset.public.filter(project=self.object).select_related('organization')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object
        context['can_update_project'] = has_perm(
            self.request.user,
            Action.UPDATE,
            self.object
        )
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('project-list'): _('Panaudojimo atvejai'),
            reverse('project-detail', args=[self.object.pk]): self.object
        }
        return context


class RemoveDatasetView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Project
    template_name = 'confirm_remove.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.object)

    def delete(self, request, *args, **kwargs):
        self.object.datasets.remove(self.kwargs.get('dataset_id'))
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('project-datasets', kwargs={'pk': self.object.pk})
