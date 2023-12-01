import json
import secrets
from datetime import datetime

import pandas as pd
import requests
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic import DetailView, View
from django.utils.text import slugify
from django.views.generic.edit import FormView
from itsdangerous import URLSafeSerializer
from reversion import set_comment
from reversion.models import Version
from reversion.views import RevisionMixin
from vitrina.helpers import prepare_email_by_identifier, get_stats_filter_options_based_on_model
from vitrina.api.models import ApiKey, ApiScope
from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain, prepare_email_by_identifier, send_email_with_logging, \
    get_stats_filter_options_based_on_model
from django.template.defaultfilters import date as _date
from vitrina import settings
from vitrina.api.models import ApiKey
from vitrina.datasets.models import Dataset
from vitrina.datasets.services import get_frequency_and_format, get_values_for_frequency, get_query_for_frequency
from vitrina.helpers import get_current_domain
from vitrina.orgs.forms import OrganizationPlanForm, OrganizationMergeForm, OrganizationUpdateForm, ApiKeyForm, \
    ApiScopeForm, ApiKeyRegenerateForm
from vitrina.orgs.forms import RepresentativeCreateForm, RepresentativeUpdateForm, PartnerRegisterForm
from vitrina.orgs.models import Organization, Representative, RepresentativeRequest
from vitrina.orgs.services import has_perm, Action, hash_api_key, manage_subscriptions_for_representative
from vitrina.plans.models import Plan
from vitrina.settings import CLIENTS_AUTH_BEARER, CLIENTS_API_URL
from vitrina.structure.models import Metadata
from vitrina.users.models import User
from vitrina.users.views import RegisterView
from vitrina.tasks.models import Task
from vitrina.views import PlanMixin, HistoryView
from allauth.socialaccount.models import SocialAccount
from vitrina.helpers import send_email_with_logging
from vitrina.messages.helpers import prepare_email_by_identifier_for_sub
from django.http import HttpResponse


class RepresentativeRequestApproveView(PermissionRequiredMixin, TemplateView):
    template_name = 'confirm_approve.html'
    base_template_content = """
        Jūsų koordinatoriaus paraiška buvo patvirtinta.   
    """
    email_identifier = "coordinator-request-approved"

    def dispatch(self, request, *args, **kwargs):
        self.representative_request = get_object_or_404(RepresentativeRequest, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_supervisor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.representative_request
        return context

    def post(self, request, *args, **kwargs):
        org = self.representative_request.organization
        user = User.objects.get(email=self.representative_request.user.email)
        if not user.organization:
            user.organization = org
        user.save()
        rep = Representative.objects.create(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            object_id=org.id,
            role=Representative.COORDINATOR,
            user=user,
            content_type=ContentType.objects.get_for_model(org)
        )
        rep.save()
        task = Task.objects.create(
            title="Naujo duomenų teikėjo: {} registracija".format(org.company_code),
            description=f"Portale užsiregistravo naujas duomenų teikėjas: {org.company_code}.",
            organization=org,
            user=user,
            status=Task.CREATED,
            type=Task.REQUEST
        )
        task.save()
        email_data = prepare_email_by_identifier_for_sub(
            self.email_identifier, self.base_template_content,
            'Koordinatoriaus paraiškos patvirtinimas',
            []
        )
        sub_email_list = [user.email]
        send_email_with_logging(email_data, sub_email_list)
        return self.get_success_url()

    def get_success_url(self):
        return redirect('/coordinator-admin/vitrina_orgs/representativerequest/')


class RepresentativeRequestDownloadView(PermissionRequiredMixin, View):
    representative_request: RepresentativeRequest

    def dispatch(self, request, *args, **kwargs):
        self.representative_request = get_object_or_404(RepresentativeRequest, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_supervisor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.representative_request
        return context

    def get(self, request, *args, **kwargs):
        file_name = self.representative_request.document.name
        response = HttpResponse(self.representative_request.document.read(), content_type="application/octet-stream")
        response['Content-Disposition'] = 'inline; filename={}'.format(file_name.split('/')[-1])
        return response


class RepresentativeRequestDenyView(PermissionRequiredMixin, TemplateView):
    representative_request: RepresentativeRequest
    template_name = 'confirm_deny.html'
    base_template_content = """
        Jūsų koordinatoriaus paraiška buvo atmesta.   
    """
    email_identifier = "coordinator-request-denied"

    def dispatch(self, request, *args, **kwargs):
        self.representative_request = get_object_or_404(RepresentativeRequest, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_supervisor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.representative_request
        return context

    def post(self, request, *args, **kwargs):
        self.representative_request.delete()
        email_data = prepare_email_by_identifier_for_sub(
            self.email_identifier, self.base_template_content,
            'Koordinatoriaus paraiškos atmetimas',
            []
        )
        sub_email_list = [self.representative_request.user.email]
        send_email_with_logging(email_data, sub_email_list)
        return self.get_success_url()

    def get_success_url(self):
        return redirect('/coordinator-admin/vitrina_orgs/representativerequest/')

class RepresentativeRequestSuspendView(PermissionRequiredMixin, TemplateView):
    representative_request: RepresentativeRequest
    template_name = 'confirm_suspend.html'
    base_template_content = """
        Jūsų koordinatoriaus teisės buvo suspenduotos.   
    """
    email_identifier = "coordinator-request-suspended"

    def dispatch(self, request, *args, **kwargs):
        self.representative_request = get_object_or_404(RepresentativeRequest, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_supervisor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.representative_request
        context['users'] = User.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        representative_role = Representative.objects.filter(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=self.representative_request.organization.id,
            user=self.representative_request.user,
            role=Representative.COORDINATOR
        ).first()
        user_to_grant_coordiantor_rights = self.request.POST.get('user')
        user_to_grant_coordiantor_rights = User.objects.filter(email=user_to_grant_coordiantor_rights).first()
        representative_role.user = user_to_grant_coordiantor_rights
        representative_role.save()
        user_to_grant_coordiantor_rights.organization = self.representative_request.organization
        user_to_grant_coordiantor_rights.save()
        email_data = prepare_email_by_identifier_for_sub(
            self.email_identifier,  self.base_template_content,
            'Koordinatoriaus paraiškos atmetimas',
            []
        )
        self.representative_request.user = user_to_grant_coordiantor_rights
        self.representative_request.save()
        sub_email_list = [self.representative_request.user.email]
        send_email_with_logging(email_data, sub_email_list)
        return self.get_success_url()

    def get_success_url(self):
        return redirect('/coordinator-admin/vitrina_orgs/representativerequest/')



class OrganizationListView(ListView):
    model = Organization
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        jurisdiction = self.request.GET.get('jurisdiction')
        orgs = Organization.public.all()
        orgs = orgs.exclude(Q(title__isnull=True) | Q(title=""))

        if query:
            orgs = orgs.filter(title__icontains=query)
        if jurisdiction:
            orgs = orgs.filter(jurisdiction=jurisdiction)
        return orgs.order_by("title")

    def get_context_data(self, **kwargs):
        context = super(OrganizationListView, self).get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()
        query = self.request.GET.get("q", "")
        context['q'] = query
        context['jurisdictions'] = [
            {
                'title': jurisdiction,
                'query': "?%s%sjurisdiction=%s" % ("q=%s" % query if query else "", "&" if query else "", jurisdiction),
                'count': filtered_queryset.filter(jurisdiction=jurisdiction).count(),
            } for jurisdiction in (
                Organization.public.values_list(
                    'jurisdiction', flat="True"
                ).distinct().order_by(
                    'jurisdiction'
                ).exclude(
                    jurisdiction__isnull=True
                )
            ) if filtered_queryset.filter(jurisdiction=jurisdiction)
        ]
        context['jurisdictions'] = sorted(context['jurisdictions'], key=lambda x: x['count'], reverse=True)
        context['selected_jurisdiction'] = self.request.GET.get('jurisdiction')
        context['jurisdiction_query'] = self.request.GET.get("jurisdiction", "")
        return context


class OrganizationManagementsView(OrganizationListView):
    title = _("Valdymo sritis")
    template_name = 'vitrina/orgs/jurisdictions.html'
    parameter_select_template_name = 'vitrina/orgs/stats_parameter_select.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        jurisdictions = context.get('jurisdictions')

        orgs = self.get_queryset()

        indicator = self.request.GET.get('indicator', None) or 'organization-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Organization.objects.order_by('created').first().created
        chart_title = ''
        yAxis_title = ''

        time_chart_data = []

        frequency, ff = get_frequency_and_format(duration)
        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        values = get_values_for_frequency(frequency, 'created')

        for jur in jurisdictions:
            count = 0
            data = []

            jurisdiction_orgs = orgs.filter(jurisdiction=jur.get('title')).order_by()

            if indicator == 'organization-count':
                items = jurisdiction_orgs.values(*values).annotate(count=Count('pk'))
                chart_title = _('Organizacijų skaičius pagal valdymo sritį laike')
                yAxis_title = _('Organizacijų skaičius')
            elif indicator == 'coordinator-count':
                items = (Representative.objects.filter(content_type=ContentType.objects.get_for_model(Organization),
                                                       role=Representative.COORDINATOR,
                                                       object_id__in=jurisdiction_orgs.values_list('pk', flat=True))
                         .values(*values).annotate(count=Count('pk')))
                chart_title = _('Koordinatorių skaičius pagal valdymo sritį laike')
                yAxis_title = _('Koordinatorių skaičius')
            else:
                items = (Representative.objects.filter(content_type=ContentType.objects.get_for_model(Organization),
                                                       role=Representative.MANAGER,
                                                       object_id__in=jurisdiction_orgs.values_list('pk', flat=True))
                         .values(*values).annotate(count=Count('pk')))
                chart_title = _('Tvarkytojų skaičius pagal valdymo sritį laike')
                yAxis_title = _('Tvarkytojų skaičius')

            for label in labels:
                label_query = get_query_for_frequency(frequency, 'created', label)
                label_count_data = items.filter(**label_query)

                if label_count_data:
                    count += label_count_data[0].get('count') or 0

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            dt = {
                'label': jur.get('title'),
                'data': data,
                'borderWidth': 1,
                'fill': True,
            }
            time_chart_data.append(dt)

        if sorting == 'sort-desc':
            jurisdictions = sorted(jurisdictions, key=lambda x: x['count'], reverse=True)
        elif sorting == 'sort-asc':
            jurisdictions = sorted(jurisdictions, key=lambda x: x['count'])
        max_count = max([x['count'] for x in jurisdictions]) if jurisdictions else 0

        context['title'] = self.title
        context['parameter_select_template_name'] = self.parameter_select_template_name
        context['time_chart_data'] = json.dumps(time_chart_data)
        context['bar_chart_data'] = jurisdictions
        context['max_count'] = max_count

        context['graph_title'] = chart_title
        context['yAxis_title'] = yAxis_title
        context['xAxis_title'] = _('Laikas')

        context['filter'] = 'jurisdiction'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['duration'] = duration

        context['has_time_graph'] = True
        context['options'] = get_stats_filter_options_based_on_model(Organization, duration, sorting, indicator)
        return context


class OrganizationDetailView(PlanMixin, DetailView):
    model = Organization
    template_name = 'vitrina/orgs/detail.html'
    plan_url_name = 'organization-plans'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        organization: Organization = self.object
        context_data['ancestors'] = organization.get_ancestors()
        context_data['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            organization
        )
        context_data['can_update_organization'] = has_perm(
            self.request.user,
            Action.UPDATE,
            Representative,
            organization
        )
        context_data['organization_id'] = organization.pk
        return context_data


class OrganizationMembersView(
    PlanMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    template_name = 'vitrina/orgs/members.html'
    context_object_name = 'members'
    paginate_by = 20
    plan_url_name = 'organization-plans'

    object: Organization

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Organization, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )

    def get_queryset(self):
        return (
            Representative.objects.
            filter(
                content_type=ContentType.objects.get_for_model(Organization),
                object_id=self.object.pk
            ).
            order_by("role", "first_name", 'last_name')
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['has_permission'] = has_perm(
            self.request.user,
            Action.CREATE,
            Representative,
            self.object,
        )
        context_data['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context_data['organization_id'] = self.object.pk
        context_data['organization'] = self.object
        return context_data


class OrganizationUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Organization
    form_class = OrganizationUpdateForm
    template_name = 'base_form.html'
    view_url_name = 'organization:edit'
    context_object_name = 'organization'

    def has_permission(self):
        org = self.get_object()
        return has_perm(self.request.user, Action.UPDATE, org)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            org = get_object_or_404(Organization, id=self.kwargs['pk'])
            return redirect(org)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Organizacijos redagavimas')
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        organization = self.get_object()
        parent = organization.get_parent()
        if parent:
            kwargs['initial'] = {'jurisdiction': parent}
        return kwargs

    def get(self, request, *args, **kwargs):
        return super(OrganizationUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.slug = slugify(self.object.title)
        self.object.save()
        if not self.object.get_parent() == form.cleaned_data['jurisdiction']:
            form.cleaned_data['jurisdiction'].fix_tree(fix_paths=True)
            self.object.move(form.cleaned_data['jurisdiction'], 'sorted-child')
        return HttpResponseRedirect(self.get_success_url())


class RepresentativeCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Representative
    form_class = RepresentativeCreateForm
    template_name = 'base_form.html'
    base_template_content = """
         Buvote įtraukti į {0} organizacijos
         narių sąrašo, tačiau nesate registruotas Lietuvos
         atvirų duomenų portale. Prašome sekite šia nuoroda,
         kad užsiregistruotumėte ir patvirtintumėte savo narystę
        'organizacijoje:\n'
        '{1}   
    """
    email_identifier = "auth-org-representative-without-credentials"

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        organization_id = self.kwargs.get('organization_id')
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_id'] = self.organization.pk
        return kwargs

    def get_success_url(self):
        return reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')})

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Representative, self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tabs'] = "vitrina/orgs/tabs.html"
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.organization,
        )
        context['representative_url'] = reverse('organization-members', args=[self.organization.pk])
        context['current_title'] = _("Tvarkytojo pridėjimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
        }
        context['organization_id'] = self.organization.pk
        return context

    def form_valid(self, form):
        self.object: Representative = form.save(commit=False)
        self.object.object_id = self.organization.pk
        self.object.content_type = ContentType.objects.get_for_model(self.organization)
        subscribe = form.cleaned_data.get('subscribe')
        try:
            user = User.objects.get(email=self.object.email)
            if self.object.role == Representative.COORDINATOR:
                user.organization = self.organization
                user.save()
        except ObjectDoesNotExist:
            user = None
        if user:
            self.object.user = user
            self.object.save()
            if not user.organization:
                user.organization = self.organization
                user.save()
            manage_subscriptions_for_representative(subscribe, user, self.organization)
        else:
            self.object.save()
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            token = serializer.dumps({"representative_id": self.object.pk})
            url = "%s%s" % (
                get_current_domain(self.request),
                reverse('representative-register', kwargs={'token': token})
            )
            email_data = prepare_email_by_identifier(
                self.email_identifier, self.base_template_content,
                'Kvietimas prisijungti prie atvirų duomenų portalo',
                [self.organization, url]
            )
            send_email_with_logging(email_data, [self.object.email])
            messages.info(self.request, _("Naudotojui išsiųstas laiškas dėl registracijos"))
        self.object.save()

        if self.object.has_api_access:
            api_key = secrets.token_urlsafe()
            ApiKey.objects.create(
                api_key=hash_api_key(api_key),
                enabled=True,
                representative=self.object
            )
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            api_key = serializer.dumps({"api_key": api_key})
            return HttpResponseRedirect(reverse('representative-api-key', args=[
                self.organization.pk,
                self.object.pk,
                api_key
            ]))

        return HttpResponseRedirect(self.get_success_url())


class RepresentativeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Representative
    form_class = RepresentativeUpdateForm
    template_name = 'base_form.html'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('organization_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object'] = self.organization
        return kwargs

    def has_permission(self):
        representative = get_object_or_404(Representative, pk=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.UPDATE, representative)

    def get_success_url(self):
        return reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tabs'] = "vitrina/orgs/tabs.html"
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.organization,
        )
        context['representative_url'] = reverse('organization-members', args=[self.organization.pk])
        context['current_title'] = _("Tvarkytojo redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
        }
        context['organization_id'] = self.organization.pk
        return context

    def form_valid(self, form):
        self.object: Representative = form.save()
        subscribe = form.cleaned_data.get('subscribe')

        if not self.object.user.organization:
            self.object.user.organization = self.organization
            self.object.user.save()

        manage_subscriptions_for_representative(subscribe, self.object.user, self.organization)
        if self.object.has_api_access:
            if not self.object.apikey_set.exists():
                api_key = secrets.token_urlsafe()
                ApiKey.objects.create(
                    api_key=hash_api_key(api_key),
                    enabled=True,
                    representative=self.object
                )

                serializer = URLSafeSerializer(settings.SECRET_KEY)
                api_key = serializer.dumps({"api_key": api_key})
                return HttpResponseRedirect(reverse('representative-api-key', args=[
                    self.organization.pk,
                    self.object.pk,
                    api_key
                ]))
            elif form.cleaned_data.get('regenerate_api_key'):
                api_key = secrets.token_urlsafe()
                api_key_obj = self.object.apikey_set.first()
                api_key_obj.api_key = hash_api_key(api_key)
                api_key_obj.enabled = True
                api_key_obj.save()

                serializer = URLSafeSerializer(settings.SECRET_KEY)
                api_key = serializer.dumps({"api_key": api_key})
                return HttpResponseRedirect(reverse('representative-api-key', args=[
                    self.organization.pk,
                    self.object.pk,
                    api_key
                ]))
        else:
            self.object.apikey_set.all().delete()

        return HttpResponseRedirect(self.get_success_url())


class RepresentativeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Representative
    template_name = 'confirm_delete.html'

    def has_permission(self):
        representative = get_object_or_404(Representative, pk=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.DELETE, representative)

    def get_success_url(self):
        return reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')})


class RepresentativeRegisterView(RegisterView):
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            token = self.kwargs.get('token')
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            data = serializer.loads(token)
            try:
                representative = Representative.objects.get(pk=data.get('representative_id'))
            except ObjectDoesNotExist:
                representative = None
            if representative:
                representative.user = user
                representative.save()

                if isinstance(representative.content_object, Organization):
                    user.organization = representative.content_object
                    user.save()
                elif isinstance(representative.content_object, Dataset):
                    user.organization = representative.content_object.organization
                    user.save()

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
        return render(request=request, template_name=self.template_name, context={"form": form})


class PartnerRegisterInfoView(TemplateView):
    template_name = 'vitrina/orgs/partners/register.html'


class PartnerRegisterView(LoginRequiredMixin, CreateView):
    form_class = PartnerRegisterForm
    template_name = 'base_form.html'

    def get(self, request, *args, **kwargs):
        user = self.request.user
        user_social_account = SocialAccount.objects.filter(user_id=user.id).first()
        if not user_social_account:
            return redirect('viisp_login')
        return super(PartnerRegisterView, self).get(request, *args, **kwargs)

    def get_form_kwargs(self):
        user = self.request.user
        user_social_account = SocialAccount.objects.filter(user_id=user.id).first()
        extra_data = {}
        company_code = extra_data.get('company_code')
        company_name = extra_data.get('company_name')
        org = Organization.objects.filter(company_code=company_code).first()
        company_name_slug = ""
        if not org and company_name:
            if len(company_name.split(' ')) > 1 and len(company_name.split(' ')) != ['']:
                for item in company_name.split(' '):
                    company_name_slug += item[0]
            else:
                company_name_slug = company_name[0]
        elif org:
            company_name_slug = org.slug
        kwargs = super().get_form_kwargs()
        initial_dict = {
            'coordinator_phone_number': extra_data.get('coordinator_phone_number'),
            'coordinator_email': user.email
        }
        kwargs['initial'] = initial_dict
        return kwargs

    def form_valid(self, form):
        representative_request = RepresentativeRequest(
            user=self.request.user,
            organization=form.cleaned_data.get('organization'),
            document=form.cleaned_data.get('request_form')
        )
        representative_request.save()

        return redirect(reverse('partner-register-complete'))


class PartnerRegisterCompleteView(TemplateView):
    template_name = 'vitrina/orgs/partners/register_complete.html'


class OrganizationPlanView(PlanMixin, TemplateView):
    template_name = 'vitrina/orgs/plans.html'
    plan_url_name = 'organization-plans'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get('status', 'opened')
        context['organization'] = self.organization
        context['organization_id'] = self.organization.pk
        if status == 'closed':
            context['plans'] = self.organization.receiver_plans.filter(is_closed=True)
        else:
            context['plans'] = self.organization.receiver_plans.filter(is_closed=False)
        context['can_manage_plans'] = has_perm(
            self.request.user,
            Action.PLAN,
            self.organization
        )
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.organization
        )
        context['history_url'] = reverse('organization-plans-history', args=[self.organization.pk])
        context['history_url_name'] = 'organization-plans-hisotry'
        context['can_manage_history'] = has_perm(
            self.request.user,
            Action.HISTORY_VIEW,
            self.organization,
        )
        context['selected_tab'] = status
        return context

    def get_plan_object(self):
        return self.organization


class OrganizationPlanCreateView(PermissionRequiredMixin, RevisionMixin, CreateView):
    model = Plan
    form_class = OrganizationPlanForm
    template_name = 'vitrina/plans/form.html'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.PLAN, self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Naujas terminas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
            reverse('organization-plans', args=[self.organization.pk]): _("Planas"),
        }
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['organizations'] = [self.organization]
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.receiver = self.organization
        self.object.save()
        set_comment(_(f'Pridėtas terminas "{self.object}".'))
        return redirect(reverse('organization-plans', args=[self.organization.pk]))


class OrganizationApiKeysView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/orgs/apikeys.html'

    object: Organization

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Organization, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.object,
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)

        headers = {
            "Authorization": CLIENTS_AUTH_BEARER}
        response = requests.get(CLIENTS_API_URL, headers=headers)
        keys = response.json()
        key_client_ids = []
        if response.status_code == 200:
            for key in keys:
                client_id = key.get('client_id')
                client_name = key.get('client_name')
                org = Organization.objects.filter(name=client_name).exists()
                if not org:
                    org = None
                key_client_ids.append(client_id)

                if not ApiKey.objects.filter(client_id=client_id).exists():
                    ApiKey.objects.create(
                        client_id=client_id,
                        client_name=client_name,
                        organization=org,
                        enabled=True
                    )
        else:
            context_data[
                'api_error'] = ('Nepavyko susisiekti su Saugyklos API, todėl raktai rodomi lentelėje gali nesutapti'
                                + ' su raktais Saugykloje.')

        keys_in_database = ApiKey.objects.all()
        for key in keys_in_database:
            if key.client_id in key_client_ids:
                key.enabled = False
                key.save()

        context_data['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.object.pk]): self.object.title,
            reverse('organization-apikeys', args=[self.object.pk]): _("Raktai"),
        }
        context_data['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object
        )
        context_data['can_update_organization'] = has_perm(
            self.request.user,
            Action.UPDATE,
            Representative,
            self.object
        )
        context_data['organization_id'] = self.object.pk
        context_data['organization'] = self.object
        internal = ApiKey.objects.filter(organization=self.object)
        scopes = ApiScope.objects.filter(organization=self.object).values_list('key_id', flat=True)
        external = ApiKey.objects.filter(pk__in=scopes).exclude(pk__in=internal)
        context_data['internal_keys'] = internal
        context_data['external_keys'] = external
        return context_data


class OrganizationApiKeysDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/orgs/apikeys_detail.html'
    pk_url_kwarg = 'apikey_id'

    object: Organization

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Organization, pk=kwargs['pk'])
        self.api_key = get_object_or_404(ApiKey, pk=kwargs['apikey_id'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.object,
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.object.pk]): self.object.title,
            reverse('organization-apikeys', args=[self.object.pk]): _("Raktai"),
        }

        context_data['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object
        )
        context_data['can_update_organization'] = has_perm(
            self.request.user,
            Action.UPDATE,
            Representative,
            self.object
        )
        context_data['organization_id'] = self.object.pk
        context_data['organization'] = self.object
        api_key = ApiKey.objects.filter(pk=self.api_key.pk).get()
        context_data['key'] = api_key

        prefix = "spinta"
        suffixes = ["_getone", "_getall", "_search", "_changes", "_insert", "_upsert", "_update", "_patch",
                    "_delete", "_wipe"]
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]

        grouped = {}
        scopes_final = {}
        scopes = ApiScope.objects.filter(key=api_key)

        for scope in scopes:
            if scope.scope == 'spinta_set_meta_fields':
                grouped.setdefault('set_meta_fields', [])
                grouped['set_meta_fields'].append(scope)
            if any((match := ext) in scope.scope for ext in suffixes):
                code = scope.scope.removeprefix(prefix).removesuffix(match)
                if len(code) > 0:
                    code = code.removeprefix('_datasets_gov_')
                    if code.startswith('_'):
                        code = code.removeprefix('_')
                else:
                    code = '(viskas)'
                grouped.setdefault(code, [])
                grouped[code].append(scope)

        for k, v in grouped.items():
            dt = {'read': False, 'write': False, 'wipe': False, 'title': '', 'url': None,
                  'enabled': False}
            if k == 'set_meta_fields':
                dt.update({'title': 'set_meta_fields'})
                for s in v:
                    if s.enabled:
                        dt.update({'enabled': True})
                scopes_final[k] = dt
            # if k == '(viskas)':
            #     dt.update({'title': '(viskas)'})
            #     for s in v:
            #         dt.update({'enabled': s.enabled})
            #     scopes_final[k] = dt
            else:
                dt.update({'title': k})
                for s in v:
                    if any(sc in s.scope for sc in read):
                        dt.update({'read': True})
                    if any(sc in s.scope for sc in write):
                        dt.update({'write': True})
                    if 'wipe' in s.scope:
                        dt.update({'wipe': True})
                    dt.update({'enabled': s.enabled})
            if k != 'set_meta_fields' and k != '(viskas)':
                org = Organization.objects.filter(name=k)
                target_dataset = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Dataset),
                    name=k)
                if org:
                    ct = ContentType.objects.get_for_model(org.get())
                    dt.update({'title': org.get().title, 'url': org.get().get_absolute_url, 'obj': org.get(), 'ct': ct})
                if target_dataset:
                    ct = ContentType.objects.get_for_model(Dataset)
                    dataset = Dataset.objects.get(pk=target_dataset.get().dataset_id)
                    dt.update({'title': dataset.title, 'url': dataset.get_absolute_url, 'obj': dataset, 'ct': ct})
            scopes_final[k] = dt
        context_data['scopes'] = scopes_final
        return context_data


class OrganizationApiKeysCreateView(PermissionRequiredMixin, CreateView):
    model = ApiKey
    form_class = ApiKeyForm
    template_name = 'base_form.html'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['current_title'] = _("Naujas raktas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.organization = self.organization
        api_key = secrets.token_urlsafe()
        self.object.api_key = hash_api_key(api_key)
        self.object.enabled = True
        self.object.save()
        permissions = ['spinta_set_meta_fields', 'spinta_getone', 'spinta_getall', 'spinta_search', 'spinta_changes']
        for p in permissions:
            ApiScope.objects.create(
                key=self.object,
                organization=self.organization,
                scope=p,
                enabled=True
            )
        messages.info(self.request, 'API raktas rodomas tik vieną kartą, todėl būtina nusikopijuoti. Sukurtas raktas:'
                      + api_key)
        return redirect(reverse('organization-apikeys', args=[self.organization.pk]))


class OrganizationApiKeysUpdateView(PermissionRequiredMixin, UpdateView):
    model = ApiKey
    form_class = ApiKeyForm
    template_name = 'base_form.html'
    pk_url_kwarg = 'apikey_id'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get('apikey_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prefix = "spinta"
        suffixes = ["_getone", "_getall", "_search", "_changes", "_insert", "_upsert", "_update", "_patch",
                    "_delete", "_wipe"]
        if self.api_key.client_id:
            headers = {
                "Authorization": CLIENTS_AUTH_BEARER}
            response = requests.get(CLIENTS_API_URL + '/' + self.api_key.client_id, headers=headers)
            if response.status_code == 200:
                if 'scopes' in response.json():
                    scopes = response.json()['scopes']

                    existing = ApiScope.objects.filter(key=self.api_key)
                    for ex in existing:
                        ex.delete()

                    for scope in scopes:
                        org = None
                        if any((match := ext) in scope for ext in suffixes):
                            code = scope.removeprefix(prefix).removesuffix(match)
                            if code:
                                org = Organization.objects.filter(name=code.removeprefix('_datasets_gov_')).get()
                        if scope != 'spinta_set_meta_fields':
                            ApiScope.objects.create(
                                key=self.api_key,
                                scope=scope,
                                enabled=True,
                                organization=org,
                                dataset=None
                            )

        context['current_title'] = _("Rakto redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save()
        return redirect(reverse('organization-apikeys', args=[self.organization.pk]))


class OrganizationApiKeysRegenerateView(PermissionRequiredMixin, UpdateView):
    model = ApiKey
    form_class = ApiKeyRegenerateForm
    template_name = 'base_form.html'
    pk_url_kwarg = 'apikey_id'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Rakto slaptažodžio keitimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.api_key = hash_api_key(form.cleaned_data.get('new_key'))
        self.object.save()
        return redirect(reverse('organization-apikeys', args=[self.organization.pk]))


class OrganizationApiKeysDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ApiKey
    template_name = 'confirm_delete.html'
    pk_url_kwarg = 'apikey_id'

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.apikey = get_object_or_404(ApiKey, pk=self.kwargs.get('apikey_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def delete(self, request, *args, **kwargs):
        # headers = {
        #     "Authorization": CLIENTS_AUTH_BEARER}
        # response = requests.delete(CLIENTS_API_URL + '/' + self.api_key.client_id, headers=headers)
        #
        self.apikey.delete()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_key'] = self.apikey
        context['current_title'] = _("Šalinti raktą")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-apikeys-detail', args=[self.organization.pk, self.apikey.pk]): self.apikey,
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def get_success_url(self):
        return reverse('organization-apikeys', kwargs={'pk': self.kwargs.get('pk')})


class OrganizationApiKeysScopeCreateView(PermissionRequiredMixin, FormView):
    form_class = ApiScopeForm
    template_name = 'base_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get('apikey_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        kwargs['api_key'] = self.api_key
        kwargs['scope'] = None
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_key'] = self.api_key
        context['current_title'] = _("Nauja taikymo sritis")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
            reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]): self.api_key,
        }
        return context

    def form_valid(self, form):
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]

        organization = None
        dataset = None

        scope_name = form.cleaned_data.get('scope')
        if scope_name == 'spinta_set_meta_fields' or scope_name == 'set_meta_fields':
            organization = self.organization
            ApiScope.objects.create(
                key=self.api_key,
                scope=scope_name,
                organization=organization,
                enabled=True
            )
        else:
            target_org = Organization.objects.filter(name=scope_name)
            metadata = Metadata.objects.filter(
                content_type=ContentType.objects.get_for_model(Dataset),
                name=scope_name)
            if target_org.exists():
                if target_org.get().pk != self.organization.pk:
                    organization = target_org.get()
                    # todo siųsti emailus
                    # url = self.api_key.get_absolute_url()
                    title = f'Prašoma prieigos prie duomenų: {self.api_key}'
                    base_email_content = """
                                        Gautas pranešimas, kad prašoma suteikti prieigą prie duomenų:
                                        {0}
                                    """
                    url = f"{get_current_domain(self.request)}{self.api_key.get_absolute_url()}"
                    rep_emails = Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(organization),
                        object_id=organization.pk).values_list('email', flat=True)
                    email_data = prepare_email_by_identifier('apikey-request', base_email_content, title,
                                                             [url])
                    send_email_with_logging(email_data, [rep_emails])
                    Task.objects.create(
                        content_type=ContentType.objects.get_for_model(ApiKey),
                        object_id=self.api_key.pk,
                        organization=target_org.get(),
                        title=f'Prašymas suteikti prieigą prie duomenų. Raktas: {self.api_key.pk}',
                        status=Task.CREATED,
                        type=Task.APIKEY,
                        description=f'Kita organizacija prašo suteikti prieigą prie duomenų raktui.'
                    )
            else:
                organization = self.organization
            if metadata.exists():
                dataset = Dataset.objects.filter(pk=metadata.get().dataset.pk).first()

        if form.cleaned_data.get('read'):
            for s in read:
                ApiScope.objects.create(
                    scope='spinta_' + scope_name + s,
                    organization=organization,
                    dataset=dataset,
                    key=self.api_key,
                    enabled=True
                )
        if form.cleaned_data.get('write'):
            for s in write:
                ApiScope.objects.create(
                    scope='spinta_' + scope_name + s,
                    organization=organization,
                    dataset=dataset,
                    key=self.api_key,
                    enabled=True
                )
        if form.cleaned_data.get('remove'):
            ApiScope.objects.create(
                scope='spinta_' + scope_name + '_wipe',
                organization=organization,
                dataset=dataset,
                key=self.api_key,
                enabled=True
            )

        return redirect(reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]))


class OrganizationApiKeysScopeChangeView(PermissionRequiredMixin, FormView):
    form_class = ApiScopeForm
    template_name = 'base_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get('apikey_id'))
        self.name = kwargs.get('scope')
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        kwargs['api_key'] = self.api_key
        kwargs['scope'] = self.name
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['api_key'] = self.api_key
        context['current_title'] = _("Taikymo srities redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
            reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]): self.api_key,
        }
        return context

    def form_valid(self, form):
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]
        create_read = False
        create_write = False
        create_wipe = False

        if self.name != 'set_meta_fields' and self.name != 'spinta_set_meta_fields':
            scopes = ApiScope.objects.filter(key=self.api_key).exclude(scope__icontains='datasets_gov')
            for sc in scopes:
                if not sc.scope == 'spinta_set_meta_fields' or not sc.scope == 'set_meta_fields':
                    if form.cleaned_data.get('read'):
                        if not any(s in sc.scope for s in read):
                            create_read = True
                    else:
                        for s in read:
                            scopes.filter(scope__icontains=s).delete()
                    if form.cleaned_data.get('write'):
                        if not any(s in sc.scope for s in write):
                            create_write = True
                    else:
                        for s in write:
                            scopes.filter(scope__icontains=s).delete()
                    if form.cleaned_data.get('remove'):
                        if 'wipe' not in sc.scope:
                            create_wipe = True
                    else:
                        scopes.filter(scope__icontains='_wipe').delete()
            if create_read:
                for s in read:
                    ApiScope.objects.create(
                        key=self.api_key,
                        scope='spinta' + s,
                        organization=self.organization,
                        enabled=True
                    )
            if create_write:
                for s in write:
                    ApiScope.objects.create(
                        key=self.api_key,
                        scope='spinta' + s,
                        organization=self.organization,
                        enabled=True
                    )
            if create_wipe:
                ApiScope.objects.create(
                    key=self.api_key,
                    scope='spinta_wipe',
                    organization=self.organization,
                    enabled=True
                )
        return redirect((reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk])))


class OrganizationApiKeysScopeObjectChangeView(PermissionRequiredMixin, FormView):
    form_class = ApiScopeForm
    template_name = 'base_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get('apikey_id'))
        self.ct = get_object_or_404(ContentType, pk=kwargs.get('content_type_id'))
        self.object = get_object_or_404(self.ct.model_class(), pk=kwargs.get('obj_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        kwargs['api_key'] = self.api_key
        kwargs['scope'] = self.object.name
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['api_key'] = self.api_key
        context['current_title'] = _("Taikymo srities redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
            reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]): self.api_key,
        }
        return context

    def form_valid(self, form):
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]
        create_read = False
        create_write = False
        create_wipe = False

        scopes = ApiScope.objects.none()

        organization = None
        dataset = None
        scope_name = self.object.name

        if isinstance(self.object, Organization):
            scopes = ApiScope.objects.filter(key=self.api_key, organization=self.object)
            organization = self.object
        else:
            scopes = ApiScope.objects.filter(key=self.api_key, dataset=self.object)
            dataset = self.object

        for sc in scopes:
            if form.cleaned_data.get('read'):
                if not any(s in sc.scope for s in read):
                    create_read = True
            else:
                for s in read:
                    scopes.filter(scope__icontains=s).delete()
            if form.cleaned_data.get('write'):
                if not any(s in sc.scope for s in write):
                    create_write = True
            else:
                for s in write:
                    scopes.filter(scope__icontains=s).delete()
            if form.cleaned_data.get('remove'):
                if 'wipe' not in sc.scope:
                    create_wipe = True
            else:
                scopes.filter(scope__icontains='_wipe').delete()

        if len(scopes) == 0:
            if form.cleaned_data.get('read'):
                create_read = True
            if form.cleaned_data.get('write'):
                create_write = True
            if form.cleaned_data.get('remove'):
                create_wipe = True

        if create_read:
            for s in read:
                ApiScope.objects.create(
                    key=self.api_key,
                    scope='spinta_datasets_gov_' + scope_name + s,
                    organization=organization,
                    dataset=dataset,
                    enabled=True
                )
        if create_write:
            for s in write:
                ApiScope.objects.create(
                    key=self.api_key,
                    scope='spinta_datasets_gov_' + scope_name + s,
                    organization=organization,
                    dataset=dataset,
                    enabled=True
                )
        if create_wipe:
            ApiScope.objects.create(
                key=self.api_key,
                scope='spinta_datasets_gov_' + scope_name + '_wipe',
                organization=organization,
                dataset=dataset,
                enabled=True
            )
        return redirect((reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk])))


class OrganizationApiKeysScopeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    model = ApiScope
    template_name = 'confirm_delete.html'

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get('apikey_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Šalinti taikymo sritį")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]): self.api_key,
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def post(self, request, *args, **kwargs):
        scope_name = kwargs.get('scope')
        api_key = kwargs.get('apikey_id')
        if scope_name == 'spinta_set_meta_fields' or scope_name == 'set_meta_fields':
            scopes = ApiScope.objects.filter(key_id=api_key, scope__contains='set_meta_fields')
            for scope in scopes:
                # todo post i api ???
                scope.delete()
        elif scope_name == '(viskas)':
            scopes = ApiScope.objects.filter(
                Q(key_id=api_key) & (
                    Q(scope='spinta_getone') |
                    Q(scope='spinta_getall') |
                    Q(scope='spinta_search') |
                    Q(scope='spinta_changes')
                    )
                )
            for scope in scopes:
                # headers = {
                #     "Authorization": CLIENTS_AUTH_BEARER}
                # response = requests.delete(CLIENTS_API_URL + '/' + self.api_key.client_id, headers=headers)
                scope.delete()
        return redirect(reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]))


class OrganizationApiKeysScopeObjectDeleteView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    model = ApiScope
    template_name = 'confirm_delete.html'

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get('apikey_id'))
        self.ct = get_object_or_404(ContentType, pk=kwargs.get('content_type_id'))
        self.object = get_object_or_404(self.ct.model_class(), pk=kwargs.get('obj_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_key'] = self.api_key
        context['current_title'] = _("Šalinti taikymo sritį")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]): self.api_key,
            reverse('organization-apikeys', args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def post(self, request, *args, **kwargs):
        if isinstance(self.object, Organization):
            scopes = ApiScope.objects.filter(key=self.api_key, organization=self.object)
        else:
            scopes = ApiScope.objects.filter(key=self.api_key, dataset=self.object)

        for sc in scopes:
            # headers = {
            #     "Authorization": CLIENTS_AUTH_BEARER}
            # response = requests.delete(CLIENTS_API_URL + '/' + self.api_key.client_id, headers=headers)
            sc.delete()
        return redirect(reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]))

    def get_success_url(self):
        return reverse('organization-apikeys-detail', kwargs={'pk': self.organization.pk,
                                                              'apikey_id': self.kwargs.get('apikey_id')})


class OrganizationApiKeysScopeToggleView(PermissionRequiredMixin, View):

    def dispatch(self, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=self.kwargs.get('apikey_id'))
        return super().dispatch(*args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get(self, request, **kwargs):
        scope_name = kwargs.get('scope')
        if scope_name == 'spinta_set_meta_fields' or scope_name == 'set_meta_fields':
            scopes = ApiScope.objects.filter(key_id=self.api_key, scope__contains='set_meta_fields')
            for scope in scopes:
                if scope.enabled:
                    scope.enabled = False
                else:
                    scope.enabled = True
                scope.save()
        elif scope_name == '(viskas)':
            scopes = ApiScope.objects.filter(
                Q(key_id=self.api_key) & (
                        Q(scope='spinta_getone') |
                        Q(scope='spinta_getall') |
                        Q(scope='spinta_search') |
                        Q(scope='spinta_changes')
                )
            )
            for scope in scopes:
                if scope.enabled:
                    scope.enabled = False
                else:
                    scope.enabled = True
                scope.save()

        # todo post enabled/disabled to spinta ???

        return redirect(reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]))


class OrganizationApiKeysScopeObjectToggleView(PermissionRequiredMixin, View):

    def dispatch(self, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.api_key = get_object_or_404(ApiKey, pk=self.kwargs.get('apikey_id'))
        self.ct = get_object_or_404(ContentType, pk=kwargs.get('content_type_id'))
        self.object = get_object_or_404(self.ct.model_class(), pk=kwargs.get('obj_id'))
        return super().dispatch(*args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get(self, request, **kwargs):
        if isinstance(self.object, Organization):
            scopes = ApiScope.objects.filter(key=self.api_key, organization=self.object)
        else:
            scopes = ApiScope.objects.filter(key=self.api_key, dataset=self.object)

        for sc in scopes:
            if sc.enabled:
                sc.enabled = False
            else:
                sc.enabled = True
            sc.save()
        # todo post enabled/disabled to spinta ???

        return redirect(reverse('organization-apikeys-detail', args=[self.organization.pk, self.api_key.pk]))


class OrganizationPlansHistoryView(PlanMixin, HistoryView):
    model = Organization
    detail_url_name = "organization-detail"
    history_url_name = "organization-plans-history"
    plan_url_name = 'organization-plans'
    tabs_template_name = 'vitrina/orgs/tabs.html'

    def get_history_objects(self):
        organization_plan_ids = Plan.objects.filter(receiver=self.object).values_list('pk', flat=True)
        return Version.objects.get_for_model(Plan).filter(
            object_id__in=list(organization_plan_ids)
        ).order_by('-revision__date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.object.pk]): self.object.title,
            reverse('organization-plans', args=[self.object.pk]): _("Planas"),
        }
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['organization_id'] = self.object.pk
        return context


class OrganizationMergeView(PermissionRequiredMixin, TemplateView):
    template_name = 'base_form.html'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Organizacijų sujungimas')
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
        }
        context['form'] = OrganizationMergeForm()
        return context

    def post(self, request, *args, **kwargs):
        form = OrganizationMergeForm(request.POST)
        if form.is_valid():
            merge_organization_id = form.cleaned_data.get('organization')
            return redirect(reverse('confirm-organization-merge', args=[
                self.organization.pk,
                merge_organization_id
            ]))
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return render(request, self.template_name, context)


class ConfirmOrganizationMergeView(RevisionMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'vitrina/orgs/confirm_merge.html'

    organization: Organization
    merge_organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('organization_id'))
        self.merge_organization = get_object_or_404(Organization, pk=kwargs.get('merge_organization_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Organizacijų sujungimas')
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
        }
        context['organization'] = self.organization
        context['merge_organization'] = self.merge_organization

        # Related objects
        context['related_objects'] = {
            _('Duomenų rinkiniai'): self.organization.dataset_set.all(),
            _('Ryšiai su duomenų rinkiniais'): self.organization.datasetattribution_set.all(),
            _('Poreikiai ir pasiūlymai'): self.organization.request_set.all(),
            _('Tvarkytojai'): Representative.objects.filter(
                content_type=ContentType.objects.get_for_model(self.organization),
                object_id=self.organization.pk,
            ),
            _('Naudotojai'): self.organization.user_set.all(),
            _('Vaikinės organizacijos'): self.organization.get_children(),
            _('Užduotys'): self.organization.task_set.all(),
            _('Harvestinimo operacija'): self.organization.harvestingjob_set.all(),
            _('Finansavimo planai'): self.organization.financingplan_set.all(),
            _('Planai (organizacija paslaugų gavėjas)'): self.organization.receiver_plans.all(),
            _('Planai (organizacija paslaugų teikėjas)'): self.organization.provider_plans.all(),
        }

        return context

    def post(self, request, *args, **kwargs):
        # Merge Dataset objects
        for obj in self.organization.dataset_set.all():
            obj.organization = self.merge_organization
            obj.save()

        # Merge DatasetAttribution objects
        for obj in self.organization.datasetattribution_set.all():
            obj.organization = self.merge_organization
            obj.save()

        # Merge Request objects
        for obj in self.organization.request_set.all():
            obj.organizations.add(self.merge_organization)
            obj.save()

        # Merge Representative objects
        rep_emails = Representative.objects.filter(
            content_type=ContentType.objects.get_for_model(self.merge_organization),
            object_id=self.merge_organization.pk
        ).values_list('email', flat=True)
        for obj in Representative.objects.filter(
                content_type=ContentType.objects.get_for_model(self.organization),
                object_id=self.organization.pk,
        ).exclude(email__in=rep_emails):
            obj.object_id = self.merge_organization.pk
            obj.save()

        # Merge User objects
        for obj in self.organization.user_set.all():
            obj.organization = self.merge_organization
            obj.save()

        # Merge Organization objects
        for obj in self.organization.get_children():
            obj.move(self.merge_organization, 'sorted-child')

        # Merge Task objects
        for obj in self.organization.task_set.all():
            obj.organization = self.merge_organization
            obj.save()

        # Merge HarvestingJob objects
        for obj in self.organization.harvestingjob_set.all():
            obj.organization = self.merge_organization
            obj.save()

        # Merge FinancingPlan objects
        for obj in self.organization.financingplan_set.all():
            obj.organization = self.merge_organization
            obj.save()

        # Merge Plan objects
        for obj in self.organization.receiver_plans.all():
            obj.receiver = self.merge_organization
            obj.save()

        for obj in self.organization.provider_plans.all():
            obj.provider = self.merge_organization
            obj.save()

        self.organization.delete()
        return redirect(reverse('organization-detail', args=[self.merge_organization.pk]))


class RepresentativeApiKeyView(PermissionRequiredMixin, TemplateView):
    template_name = 'vitrina/orgs/api_key.html'

    organization: Organization
    representative: Representative

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        self.representative = get_object_or_404(Representative, pk=kwargs.get('rep_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.organization,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        serializer = URLSafeSerializer(settings.SECRET_KEY)
        api_key = kwargs.get('key')
        data = serializer.loads(api_key)
        context['api_key'] = data.get('api_key')
        context['url'] = reverse('organization-members', args=[self.organization.pk])
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
            reverse('organization-members', args=[self.organization.pk]): _("Tvarkytojai"),
        }
        return context
