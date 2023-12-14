import secrets

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, View
from django.views.generic.edit import DeleteView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.api.models import ApiKey, ApiScope
from vitrina.api.services import get_auth_session
from vitrina.datasets.models import Dataset
from vitrina.messages.models import Subscription
from vitrina.orgs.forms import ProjectApiKeyRegenerateForm, ProjectApiKeyForm
from vitrina.orgs.services import has_perm, Action, hash_api_key
from vitrina.projects.forms import ProjectForm
from vitrina.projects.models import Project
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.models import Metadata, Property
from vitrina.tasks.models import Task
from vitrina.views import HistoryMixin, HistoryView
from vitrina.helpers import get_current_domain


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
        context['has_perm'] = has_perm(
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


class ProjectPermissionsView(HistoryMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'vitrina/projects/permissions.html'

    object: Project
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_PROJECT_KEYS,
            self.object
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # todo
        viisp_authorized = True
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
        apikey_ids = ApiKey.objects.filter(project=self.object).values_list('pk', flat=True)
        scopes = ApiScope.objects.filter(key__in=apikey_ids)
        grouped = {}
        datasets = self.object.datasets.all()
        for sc in scopes:
            grouped.setdefault(sc.dataset, [])
            grouped[sc.dataset].append(sc)
        for d in datasets:
            if d not in grouped:
                grouped.setdefault(d, [])
                grouped[d].append([])
        if apikey_ids:
            context['project_key'] = ApiKey.objects.filter(pk__in=apikey_ids).first()
        context['scopes'] = grouped
        context['viisp_authorized'] = viisp_authorized
        return context


class ProjectApiKeysCreateView(PermissionRequiredMixin, CreateView):
    model = ApiKey
    form_class = ProjectApiKeyForm
    template_name = 'base_form.html'

    project: Project

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_PROJECT_KEYS,
            self.project
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.project
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['current_title'] = _("Naujas raktas")
        context['parent_links'] = {
            reverse('project-list'): _('Projektai'),
            reverse('project-detail', args=[self.project.pk]): self.project.title,
            reverse('project-permissions', args=[self.project.pk]): _("Leidimai"),
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.project = self.project
        permissions = ["_getone", "_getall", "_search", "_changes"]
        api_key = secrets.token_urlsafe()
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        data = {
            'secret': api_key,
            'scopes': []
        }
        scopes_to_post = []
        response = get_auth_session().post(SPINTA_SERVER_URL + '/auth/clients', json=data, headers=headers)
        if response.status_code == 200:
            if 'client_id' in response.json() and 'client_name' in response.json():
                self.object.client_id = response.json()['client_id']
                self.object.client_name = response.json()['client_name']
                self.object.api_key = hash_api_key(api_key)
                self.object.enabled = True
                self.object.save()

                datasets = self.project.datasets.all()
                url = f"{get_current_domain(self.request)}/projects/" \
                    f"{self.project.pk}/permissions/{self.object.pk}"

                for d in datasets:
                    meta = d.metadata.first()
                    if meta:
                        for p in permissions:
                            sc = 'spinta_' + meta.name + p
                            ApiScope.objects.create(
                                key=self.object,
                                dataset=d,
                                scope=sc,
                                enabled=None
                            )
                            scopes_to_post.append(sc)
                        Task.objects.create(
                            title="Naujas duomenų leidimo prašymas rinkiniui: {}".format(d.title),
                            description=f"Portale prie duomenų rinkinio prašoma suteikti prieigą panaudos atvejui:"
                                        f" {self.project.title}." +
                                        f"<br/><a href=" + url + ">Peržiūrėti leidimus</a>.",
                            organization=d.organization,
                            status=Task.CREATED,
                            type=Task.REQUEST
                        )
                new_scopes = {
                    'scopes': scopes_to_post
                }
                resp = get_auth_session().patch(SPINTA_SERVER_URL + '/auth/clients/' + response.json()['client_id'],
                                                json=new_scopes, headers=headers)
                if not resp.status_code == 200:
                    messages.error(self.request, _('Saugant API raktą įvyko klaida.'))
                messages.info(self.request, _('API raktas rodomas tik vieną kartą, todėl būtina nusikopijuoti.'
                                              ' Sukurtas raktas:' + api_key))
        else:
            messages.error(self.request, _('Saugant API raktą įvyko klaida.'))
        return redirect(reverse('project-permissions', args=[self.project.pk]))


class ProjectPermissionsCreateView(PermissionRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_PROJECT_KEYS,
            self.project
        )

    def get(self, request, **kwargs):
        project_id = kwargs.get('pk')
        project = get_object_or_404(Project, pk=project_id)
        apikey = ApiKey.objects.filter(project_id=project_id).first()
        permissions = ["_getone", "_getall", "_search", "_changes"]

        datasets = project.datasets.all()
        metadata = Metadata.objects.filter(content_type=ContentType.objects.get_for_model(Property),
                                           dataset__in=datasets, access=Metadata.PUBLIC)

        if apikey:
            scopes = ApiScope.objects.filter(key=apikey)
            url = f"{get_current_domain(self.request)}/projects/" \
                  f"{project_id}/permissions/{apikey.pk}"
            for m in metadata:
                code = m.name
                for sc in scopes:
                    action = sc.scope.removeprefix('spinta_' + code)
                    if action in permissions:
                        permissions.remove(action)
                if len(permissions) > 0:
                    for p in permissions:
                        ApiScope.objects.create(
                            key=apikey,
                            dataset=m.dataset,
                            scope='spinta_' + code + p,
                            enabled=None
                        )
                    Task.objects.create(
                        title="Naujas duomenų leidimo prašymas rinkiniui: {}".format(m.dataset.title),
                        description=f"Portale prie duomenų rinkinio prašoma suteikti prieigą panaudos atvejui:"
                                    f" {project.title}." +
                                    f"<br/><a href=" + url + ">Peržiūrėti leidimus</a>.",
                        organization=m.dataset.organization,
                        status=Task.CREATED,
                        type=Task.REQUEST
                    )
        else:
            return redirect(reverse('project-apikeys-create', args=[self.project.pk]))
        return redirect(reverse('project-permissions', args=[self.project.pk]))


class ProjectPermissionsToggleView(PermissionRequiredMixin, View):
    def dispatch(self, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs.get('pk'))
        self.apikey = get_object_or_404(ApiKey, pk=kwargs.get('apikey_id'))
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('dataset_id'))
        return super().dispatch(*args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_PROJECT_KEYS,
            self.project,
        )

    def get(self, request, **kwargs):
        scopes = ApiScope.objects.filter(key=self.apikey, dataset=self.dataset)
        scope_list = []
        for sc in scopes:
            if sc.enabled:
                sc.enabled = False
                sc.save()
            else:
                sc.enabled = True
                sc.save()
                scope_list.append(sc)
        existing = (ApiScope.objects.filter(key=self.apikey, dataset=self.dataset, enabled=True)
                    .values_list('scope', flat=True))
        ex_list = list(existing)
        for s in scope_list:
            if s not in ex_list:
                ex_list.append(s)
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        data = {
            'scopes': ex_list
        }
        response = get_auth_session().post(SPINTA_SERVER_URL + '/auth/clients' + self.apikey.client_id,
                                           json=data, headers=headers)
        if response.status_code != 200:
            messages.error(self.request, _('Saugant API raktą įvyko klaida.'))

        return redirect(reverse('project-apikeys-detail', args=[self.project.pk, self.apikey.pk]))


class ProjectApiKeysDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/projects/apikeys_detail.html'
    pk_url_kwarg = 'apikey_id'

    object: Project

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Project, pk=kwargs['pk'])
        self.api_key = get_object_or_404(ApiKey, pk=kwargs['apikey_id'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_PROJECT_KEYS,
            self.object,
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('project-list'): _('Projektai'),
            reverse('project-detail', args=[self.object.pk]): self.object.title,
            reverse('project-permissions', args=[self.object.pk]): _("Leidimai"),
        }

        context_data['project_id'] = self.object.pk
        context_data['project'] = self.object
        api_key = ApiKey.objects.filter(pk=self.api_key.pk).get()
        context_data['key'] = api_key

        scopes = ApiScope.objects.filter(key=api_key)
        grouped = {}
        for scope in scopes:
            grouped.setdefault(scope.dataset, [])
            grouped[scope.dataset].append(scope)
        context_data['scopes'] = grouped
        return context_data


class ProjectApiKeysRegenerateView(PermissionRequiredMixin, UpdateView):
    model = ApiKey
    form_class = ProjectApiKeyRegenerateForm
    template_name = 'base_form.html'
    pk_url_kwarg = 'apikey_id'

    project: Project

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['pk'])
        self.apikey = get_object_or_404(ApiKey, pk=kwargs['apikey_id'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_PROJECT_KEYS,
            self.project,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.project
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['can_update_project'] = has_perm(
            self.request.user,
            Action.UPDATE,
            self.project
        )
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('project-list'): _('Panaudojimo atvejai'),
            reverse('project-detail', args=[self.project.pk]): self.project
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.api_key = hash_api_key(form.cleaned_data.get('new_key'))
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        data = {
            'secret': form.cleaned_data.get('new_key')
        }
        response = get_auth_session().post(SPINTA_SERVER_URL + '/auth/clients/' + self.apikey.client_name,
                                           json=data, headers=headers)
        if response.status_code == 200:
            self.object.save()
        else:
            if response.status_code != 200:
                messages.error(self.request, _('Saugant API raktą įvyko klaida.'))
        return redirect(reverse('project-permissions', args=[self.project.pk]))


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
