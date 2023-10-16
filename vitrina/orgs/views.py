import json
import secrets
from datetime import datetime

import pandas as pd
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.models import Q, Sum, Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic import DetailView, View
from django.utils.text import slugify
from itsdangerous import URLSafeSerializer
from reversion import set_comment
from reversion.models import Version
from reversion.views import RevisionMixin
from vitrina import settings
from vitrina.api.models import ApiKey
from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain, prepare_email_by_identifier
from django.template.defaultfilters import date as _date
from vitrina import settings
from vitrina.api.models import ApiKey
from vitrina.datasets.models import Dataset
from vitrina.datasets.services import get_frequency_and_format, get_values_for_frequency, get_query_for_frequency
from vitrina.helpers import get_current_domain
from vitrina.orgs.forms import OrganizationPlanForm, OrganizationMergeForm, OrganizationUpdateForm
from vitrina.orgs.forms import RepresentativeCreateForm, RepresentativeUpdateForm, PartnerRegisterForm
from vitrina.orgs.models import Organization, Representative, RepresentativeRequest
from vitrina.orgs.services import has_perm, Action, hash_api_key
from vitrina.plans.models import Plan
from vitrina.users.models import User
from vitrina.users.views import RegisterView
from vitrina.tasks.models import Task
from allauth.socialaccount.models import SocialAccount
from treebeard.mp_tree import MP_Node
from vitrina.views import PlanMixin, HistoryView
from allauth.socialaccount.models import SocialAccount


class RepresenentativeRequestApproveView(PermissionRequiredMixin, TemplateView):
    representative_request: RepresentativeRequest
    template_name = 'confirm_approve.html'

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
        company_code = self.representative_request.org_code
        org = Organization.objects.filter(company_code=company_code).first()
        if not org:
            org = Organization.add_root(
                title=self.representative_request.org_name,
                company_code=company_code,
                slug=slugify(self.representative_request.org_slug)
            )

        user = User.objects.get(email=self.representative_request.user.email)

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
        self.representative_request.delete()
        return self.get_success_url()

    def get_success_url(self):
        return redirect('/coordinator-admin/vitrina_orgs/representativerequest/')

class RepresenentativeRequestDenyView(PermissionRequiredMixin, TemplateView):
    representative_request: RepresentativeRequest
    template_name = 'confirm_deny.html'

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
        start_date = Organization.objects.all().first().created

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
            elif indicator == 'coordinator-count':
                items = (Representative.objects.filter(content_type=ContentType.objects.get_for_model(Organization),
                                                       role=Representative.COORDINATOR,
                                                       object_id__in=jurisdiction_orgs.values_list('pk', flat=True))
                         .values(*values).annotate(count=Count('pk')))
            else:
                items = (Representative.objects.filter(content_type=ContentType.objects.get_for_model(Organization),
                                                       role=Representative.MANAGER,
                                                       object_id__in=jurisdiction_orgs.values_list('pk', flat=True))
                         .values(*values).annotate(count=Count('pk')))

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

        context['filter'] = 'jurisdiction'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['duration'] = duration

        context['has_time_graph'] = True
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
        else:
            self.object.save()
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            token = serializer.dumps({"representative_id": self.object.pk})
            url = "%s%s" % (
                get_current_domain(self.request),
                reverse('representative-register', kwargs={'token': token})
            )
            email_data = prepare_email_by_identifier(
                self.email_identifier,  self.base_template_content,
                'Kvietimas prisijungti prie atvirų duomenų portalo',
                 [self.organization, url]
             )
            send_mail(
                subject=_(email_data['email_subject']),
                message=_(email_data['email_content']),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.object.email],
            )
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

        if not self.object.user.organization:
            self.object.user.organization = self.organization
            self.object.user.save()
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
        extra_data = user_social_account.extra_data
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
            'coordinator_first_name': user.first_name,
            'coordinator_last_name': user.last_name,
            'coordinator_phone_number': extra_data.get('coordinator_phone_number'),
            'coordinator_email': user.email,
            'company_code': company_code,
            'company_name': company_name,
            'company_slug': company_name_slug,
            'company_slug_read_only': True if org else False
        }
        kwargs['initial'] = initial_dict
        return kwargs

    def form_valid(self, form):
        representative_request = RepresentativeRequest(
            user = self.request.user,
            document = form.cleaned_data.get('request_form'),
            org_code = form.cleaned_data.get('company_code'),
            org_name = form.cleaned_data.get('company_name'),
            org_slug = form.cleaned_data.get('company_slug')
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
