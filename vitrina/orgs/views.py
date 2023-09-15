import secrets

import numpy as np
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic import DetailView
from django.utils.text import slugify
from itsdangerous import URLSafeSerializer
from reversion import set_comment
from reversion.models import Version
from reversion.views import RevisionMixin

from vitrina import settings
from vitrina.api.models import ApiKey
from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain
from vitrina.orgs.forms import OrganizationPlanForm, OrganizationMergeForm
from vitrina.orgs.forms import RepresentativeCreateForm, RepresentativeUpdateForm, PartnerRegisterForm
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.plans.models import Plan
from vitrina.users.models import User
from vitrina.users.views import RegisterView
from vitrina.tasks.models import Task
from allauth.socialaccount.models import SocialAccount
from treebeard.mp_tree import MP_Node

from vitrina.views import PlanMixin, HistoryView


class OrganizationListView(ListView):
    model = Organization
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        jurisdiction = self.request.GET.get('jurisdiction')
        orgs = Organization.public.all()

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
    template_name = 'vitrina/orgs/jurisdictions.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        jurisdictions = context.get('jurisdictions')
        if sorting == 'sort-desc':
            jurisdictions = sorted(jurisdictions, key=lambda x: x['count'], reverse=True)
        elif sorting == 'sort-asc':
            jurisdictions = sorted(jurisdictions, key=lambda x: x['count'])
        max_count = max([x['count'] for x in jurisdictions]) if jurisdictions else 0

        context['jurisdiction_data'] = jurisdictions
        context['max_count'] = max_count
        context['filter'] = 'jurisdiction'
        context['sort'] = sorting
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
        return context_data


class RepresentativeCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Representative
    form_class = RepresentativeCreateForm
    template_name = 'base_form.html'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        organization_id = self.kwargs.get('organization_id')
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_id'] = self.kwargs.get('object_id')
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
            send_mail(
                subject=_('Kvietimas prisijungti prie atvirų duomenų portalo'),
                message=_(
                    f'Buvote įtraukti į „{self.organization}“ organizacijos '
                    'narių sąrašo, tačiau nesate registruotas Lietuvos '
                    'atvirų duomenų portale. Prašome sekite šia nuoroda, '
                    'kad užsiregistruotumėte ir patvirtintumėte savo narystę '
                    'organizacijoje:\n'
                    '\n'
                    f'{url}\n'
                    '\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.object.email],
            )
            messages.info(self.request, _("Naudotojui išsiųstas laiškas dėl registracijos"))
        self.object.save()

        if self.object.has_api_access:
            ApiKey.objects.create(
                api_key=secrets.token_urlsafe(),
                enabled=True,
                representative=self.object
            )

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
                ApiKey.objects.create(
                    api_key=secrets.token_urlsafe(),
                    enabled=True,
                    representative=self.object
                )
            elif form.cleaned_data.get('regenerate_api_key'):
                api_key = self.object.apikey_set.first()
                api_key.api_key = secrets.token_urlsafe()
                api_key.enabled = True
                api_key.save()
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
        if user_social_account:
            extra_data = user_social_account.extra_data
            company_code = extra_data.get('company_code')
            company_name = extra_data.get('company_name')
        else:
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
            if len(company_name.split(' ')) > 1 and len(company_name.split(' ')) != [''] :
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
            'company_name':company_name,
            'company_slug': company_name_slug,
            'company_slug_read_only': True if org else False
        }
        kwargs['initial'] = initial_dict
        return kwargs

    def form_valid(self, form):
        company_code = form.cleaned_data.get('company_code')
        org = Organization.objects.filter(company_code=company_code).first()
        if org:
            self.org = org
        else:
            Organization.fix_tree(fix_paths=True)
            self.org = Organization.add_root(
                title=form.cleaned_data.get('company_name'),
                company_code=company_code,
                slug=slugify(form.cleaned_data.get('company_slug'))
            )
    
        user = User.objects.get(email=form.cleaned_data.get('coordinator_email'))
        user.phone = form.cleaned_data.get('coordinator_phone_number')
        user.save()

        rep = Representative.objects.create(
            email=form.cleaned_data.get('coordinator_email'),
            first_name=form.cleaned_data.get('coordinator_first_name'),
            last_name=form.cleaned_data.get('coordinator_last_name'),
            phone=form.cleaned_data.get('coordinator_phone_number'),
            object_id=self.org.id,
            role=Representative.COORDINATOR,
            user=self.request.user,
            content_type=ContentType.objects.get_for_model(self.org)
        )
        rep.save()
        task = Task.objects.create(
            title="Naujo duomenų teikėjo: {} registracija".format(self.org.company_code),
            description=f"Portale užsiregistravo naujas duomenų teikėjas: {self.org.company_code}.",
            organization=self.org,
            user=self.request.user,
            status=Task.CREATED,
            type=Task.REQUEST
        )
        task.save()
        return redirect(self.org)


def get_path(
    value: int,
    steplen: int = MP_Node.steplen,
    alphabet: str = MP_Node.alphabet,
) -> str:
    return MP_Node._int2str(value).rjust(steplen, alphabet[0])


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
