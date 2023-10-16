from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views.generic.edit import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.datasets.models import Dataset
from vitrina.messages.models import Subscription
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.forms import ProjectForm
from vitrina.projects.models import Project
from vitrina.tasks.models import Task
from vitrina.views import HistoryMixin, HistoryView
from vitrina.helpers import prepare_email_by_identifier
from django.core.mail import send_mail
from vitrina import settings


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
                try:
                    send_mail(
                        subject=_(email_data['email_subject']),
                        message=_(email_data['email_content']),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[self.object.user.email],
                    )
                except Exception as e:
                    import logging
                    logging.warning("Email was not send ", _(email_data['email_subject']),
                                    _(email_data['email_content']), [self.object.user.email], e)
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
