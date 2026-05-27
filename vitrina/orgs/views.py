import json
import logging
import secrets
from datetime import datetime
from json import JSONDecodeError
from typing import List, Any

import pandas as pd
import requests
from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q, Count, QuerySet, Case, When, IntegerField
from django.forms import BaseForm
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from django.views.generic import DetailView, View
from django.utils.text import slugify
from django.views.generic.edit import FormView
from haystack.generic_views import SearchView
from itsdangerous import URLSafeSerializer, BadSignature
from requests import Response
from reversion.models import Version

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.permissions import can_view_organization_agreements, can_view_organization_agreement
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.mixins import (
    AgreementNegotiateMixin,
    AgreementApproveMixin,
    AgreementSignMixin,
    AgreementFormMixin,
)
from vitrina.smart_contracts.models import Agreement
from vitrina.smart_contracts.permissions import (
    can_approve_agreements,
    can_form_agreements,
    can_sign_agreements,
    can_upload_agreement_file,
)
from vitrina.smart_contracts.services import get_agreements
from vitrina.smart_contracts.views import BaseAgreementListView, BaseAgreementDetailView
from vitrina.statistics.helpers import get_start_date_based_on_frequency
from vitrina.messages.models import SentMail
from vitrina.orgs.helpers import get_or_create_parent_org
from vitrina.requests.models import RequestAssignment
from vitrina.helpers import get_stats_filter_options_based_on_model, build_page_title_context
from vitrina.api.services import get_auth_session
from vitrina.helpers import (
    prepare_email_by_identifier,
)
from vitrina.api.models import ApiKey, ApiScope
from vitrina.datasets.models import (
    Dataset,
    Contact,
)
from vitrina.helpers import (
    get_current_domain,
    send_email_with_logging,
    email,
)
from django.template.defaultfilters import date as _date
from vitrina import settings
from vitrina.datasets.services import (
    get_frequency_and_format,
    get_values_for_frequency,
    get_query_for_frequency,
)
from vitrina.datasets.services import (
    manage_subscriptions_for_representative as manage_dataset_subscriptions,
)
from vitrina.orgs.forms import (
    OrganizationPlanForm,
    OrganizationMergeForm,
    OrganizationUpdateForm,
    OrganizationCreateForm,
    ApiKeyForm,
    ApiScopeForm,
    ApiKeyRegenerateForm,
    OrganizationSearchForm,
    ContactCreateForm,
    ContactUpdateForm,
)
from vitrina.orgs.forms import (
    RepresentativeCreateForm,
    RepresentativeUpdateForm,
    PartnerRegisterForm,
)
from vitrina.orgs.models import Organization, Representative, RepresentativeRequest
from vitrina.orgs.services import (
    has_perm,
    Action,
    hash_api_key,
    manage_subscriptions_for_representative,
    pre_representative_delete,
)
from vitrina.plans.models import Plan
from vitrina.projects.models import Project
from vitrina.projects.services import get_projects
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.models import Metadata
from vitrina.structure.services import get_data_from_spinta
from vitrina.uapi.models import Agent
from vitrina.users.forms import RepresentativeRegisterForm
from vitrina.users.models import User
from vitrina.users.views import RegisterView
from vitrina.tasks.models import Task
from vitrina.views import PlanMixin, HistoryView
from django.http import HttpResponse


logger = logging.getLogger()


class OrganizationBaseViewMixin:
    plan_url_name = "organization-plans"
    organization_url_kwarg = "pk"

    def setup(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get(self.organization_url_kwarg))
        return super().setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["can_view_members"] = has_perm(self.request.user, Action.VIEW, Representative, self.organization)
        context_data["can_view_contacts"] = has_perm(self.request.user, Action.VIEW, Contact, self.organization)
        context_data["can_update_organization"] = has_perm(
            self.request.user, Action.UPDATE, Representative, self.organization
        )
        context_data["can_view_agents"] = has_perm(self.request.user, Action.VIEW, Agent, self.organization)
        context_data["can_view_keys"] = has_perm(self.request.user, Action.MANAGE_KEYS, Organization, self.organization)
        context_data["organization"] = self.organization
        context_data["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-detail", args=[self.organization.pk]): self.organization,
        }
        context_data["tabs"] = "vitrina/orgs/tabs.html"
        return context_data

    def get_plan_object(self) -> Organization:
        return self.organization


class RepresentativeRequestApproveView(PermissionRequiredMixin, TemplateView):
    template_name = "confirm_approve.html"
    email_identifier = "coordinator-request-approved"

    def dispatch(self, request, *args, **kwargs):
        self.representative_request = get_object_or_404(RepresentativeRequest, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_supervisor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.representative_request
        return context

    def post(self, request, *args, **kwargs):
        org = self.representative_request.organization
        user = self.representative_request.user
        if not user.organization:
            user.organization = org
        user.save()
        if not Representative.objects.filter(
            user=user,
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.id,
        ):
            rep = Representative.objects.create(
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=self.representative_request.phone,
                object_id=org.id,
                role=Representative.OPEN_DATA_COORDINATOR,
                user=user,
                content_type=ContentType.objects.get_for_model(org),
            )
            rep.save()

        self.representative_request.status = RepresentativeRequest.APPROVED
        self.representative_request.save()

        task = Task.objects.create(
            title="Naujo duomenų teikėjo: {} registracija".format(org.company_code),
            description=f"Portale užsiregistravo naujas duomenų teikėjas: {org.company_code}.",
            organization=org,
            user=user,
            status=Task.CREATED,
            type=Task.REQUEST,
        )
        task.save()

        sub_email_list = [user.email]
        organization_url = "%s%s" % (
            get_current_domain(self.request),
            reverse("organization-detail", args=[org.pk]),
        )

        email(
            sub_email_list,
            self.email_identifier,
            "vitrina/orgs/emails/representative_created.md",
            {"user": user.first_name, "link": organization_url},
        )

        return self.get_success_url()

    def get_success_url(self):
        return redirect("/coordinator-admin/vitrina_orgs/representativerequest/")


class RepresentativeRequestDownloadView(PermissionRequiredMixin, View):
    representative_request: RepresentativeRequest

    def dispatch(self, request, *args, **kwargs):
        self.representative_request = get_object_or_404(RepresentativeRequest, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_supervisor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.representative_request
        return context

    def get(self, request, *args, **kwargs):
        file_name = self.representative_request.document.name
        response = HttpResponse(
            self.representative_request.document.read(),
            content_type="application/octet-stream",
        )
        response["Content-Disposition"] = "inline; filename={}".format(file_name.split("/")[-1])
        return response


class RepresentativeRequestDenyView(PermissionRequiredMixin, TemplateView):
    representative_request: RepresentativeRequest
    template_name = "confirm_deny.html"
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
        context["object"] = self.representative_request
        return context

    def post(self, request, *args, **kwargs):
        self.representative_request.status = RepresentativeRequest.REJECTED
        self.representative_request.save()
        sub_email_list = [self.representative_request.user.email]
        email(
            sub_email_list,
            self.email_identifier,
            "vitrina/emails/request_denied.md",
            {"user": self.representative_request.user},
        )

        return self.get_success_url()

    def get_success_url(self):
        return redirect("/coordinator-admin/vitrina_orgs/representativerequest/")


class RepresentativeRequestSuspendView(PermissionRequiredMixin, TemplateView):
    representative_request: RepresentativeRequest
    template_name = "confirm_suspend.html"

    def dispatch(self, request, *args, **kwargs):
        self.representative_request = get_object_or_404(RepresentativeRequest, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user.is_supervisor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.representative_request
        context["users"] = User.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        representative_role = Representative.objects.filter(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=self.representative_request.organization.id,
            user=self.representative_request.user,
            role__in=Representative.COORDINATOR_ROLES,
        ).first()
        user_to_grant_coordiantor_rights = self.request.POST.get("user")
        user_to_grant_coordiantor_rights = User.objects.filter(email=user_to_grant_coordiantor_rights).first()
        representative_role.user = user_to_grant_coordiantor_rights
        representative_role.save()
        user_to_grant_coordiantor_rights.organization = self.representative_request.organization
        user_to_grant_coordiantor_rights.save()
        self.representative_request.user = user_to_grant_coordiantor_rights
        self.representative_request.save()
        return self.get_success_url()

    def get_success_url(self):
        return redirect("/coordinator-admin/vitrina_orgs/representativerequest/")


class OrganizationListView(SearchView):
    template_name = "vitrina/orgs/list.html"
    form_class = OrganizationSearchForm
    paginate_by = 20

    def get_queryset(self):
        organizations = super().get_queryset()
        jurisdiction_id = self.request.GET.get("jurisdiction")
        organizations = organizations.models(Organization)

        if jurisdiction_id:
            if not jurisdiction_id.isdigit():
                jurisdiction_id = 1  # unassigned

            organizations = organizations.filter(jurisdiction=jurisdiction_id)
        return organizations.order_by("title_s")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()
        query = self.request.GET.get("q", "")
        context["q"] = query

        jurisdictions = Organization.public.values_list("jurisdiction_id", flat=True).distinct()
        jurisdictions_objects = {
            jurisdiction: AreaOfManagement.objects.filter(id=jurisdiction).first() for jurisdiction in jurisdictions
        }

        context["jurisdictions"] = [
            {
                "id": aom_object.id,
                "title": str(aom_object),
                "query": "?%s%sjurisdiction=%s"
                % (
                    "q=%s" % query if query else "",
                    "&" if query else "",
                    aom_object.id,
                ),
                "count": filtered_queryset.filter(jurisdiction=aom_id).count(),
            }
            for aom_id, aom_object in jurisdictions_objects.items()
            if filtered_queryset.filter(jurisdiction=aom_id)
        ]
        context["jurisdictions"] = sorted(context["jurisdictions"], key=lambda x: x["count"], reverse=True)

        selected_jurisdiction_id = self.request.GET.get("jurisdiction")
        if selected_jurisdiction_id is None or not selected_jurisdiction_id.isdigit():
            selected_jurisdiction_id = None
        selected_jurisdiction = AreaOfManagement.objects.filter(id=selected_jurisdiction_id).first()
        context["selected_jurisdiction"] = str(selected_jurisdiction) if selected_jurisdiction else None

        context["jurisdiction_query"] = self.request.GET.get("jurisdiction", "")
        return context


class OrganizationManagementsView(OrganizationListView):
    title = _("Valdymo sritis")
    template_name = "vitrina/orgs/jurisdictions.html"
    parameter_select_template_name = "vitrina/orgs/stats_parameter_select.html"
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        jurisdictions = context.get("jurisdictions")

        orgs = self.get_queryset()

        indicator = self.request.GET.get("indicator", None) or "organization-count"
        sorting = self.request.GET.get("sort", None) or "sort-desc"
        duration = self.request.GET.get("duration", None) or "duration-yearly"

        chart_title = ""
        yAxis_title = ""

        time_chart_data = []

        frequency, ff = get_frequency_and_format(duration)
        end_date = datetime.now()
        start_date = get_start_date_based_on_frequency(frequency, end_date)
        labels = pd.period_range(start=start_date, end=end_date, freq=frequency).tolist()
        values = get_values_for_frequency(frequency, "created")

        for jur in jurisdictions:
            data = []
            jurisdiction_orgs = orgs.filter(jurisdiction=jur["id"]).order_by()

            if indicator == "organization-count":
                items = (
                    Organization.objects.filter(pk__in=jurisdiction_orgs.values_list("pk", flat=True))
                    .values(*values)
                    .annotate(count=Count("pk"))
                )
                chart_title = _("Organizacijų skaičius pagal valdymo sritį laike")
                yAxis_title = _("Organizacijų skaičius")
            elif indicator == "coordinator-count":
                items = (
                    Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(Organization),
                        role__in=Representative.COORDINATOR_ROLES,
                        object_id__in=jurisdiction_orgs.values_list("pk", flat=True),
                    )
                    .values(*values)
                    .annotate(count=Count("pk"))
                )
                chart_title = _("Koordinatorių skaičius pagal valdymo sritį laike")
                yAxis_title = _("Koordinatorių skaičius")
            else:
                items = (
                    Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(Organization),
                        role__in=Representative.MANAGER_ROLES,
                        object_id__in=jurisdiction_orgs.values_list("pk", flat=True),
                    )
                    .values(*values)
                    .annotate(count=Count("pk"))
                )
                chart_title = _("Tvarkytojų skaičius pagal valdymo sritį laike")
                yAxis_title = _("Tvarkytojų skaičius")

            for label in labels:
                count = 0
                label_query = get_query_for_frequency(frequency, "created", label)
                label_count_data = items.filter(**label_query)

                if label_count_data:
                    count += sum(item.get("count", 0) for item in label_count_data)

                if frequency == "W":
                    data.append({"x": _date(label.start_time, ff), "y": count})
                else:
                    data.append({"x": _date(label, ff), "y": count})

            dt = {
                "label": jur.get("title"),
                "data": data,
                "borderWidth": 1,
                "fill": True,
            }
            time_chart_data.append(dt)

        if sorting == "sort-desc":
            jurisdictions = sorted(jurisdictions, key=lambda x: x["count"], reverse=True)
        elif sorting == "sort-asc":
            jurisdictions = sorted(jurisdictions, key=lambda x: x["count"])
        max_count = max([x["count"] for x in jurisdictions]) if jurisdictions else 0

        context["title"] = self.title
        context["parameter_select_template_name"] = self.parameter_select_template_name
        context["time_chart_data"] = json.dumps(time_chart_data)
        context["bar_chart_data"] = jurisdictions
        context["max_count"] = max_count

        context["graph_title"] = chart_title
        context["yAxis_title"] = yAxis_title
        context["xAxis_title"] = _("Laikas")

        context["filter"] = "jurisdiction"
        context["active_indicator"] = indicator
        context["sort"] = sorting
        context["duration"] = duration

        context["has_time_graph"] = True
        context["options"] = get_stats_filter_options_based_on_model(Organization, duration, sorting, indicator)
        return context


class OrganizationDetailView(PermissionRequiredMixin, PlanMixin, OrganizationBaseViewMixin, DetailView):
    model = Organization
    template_name = "vitrina/orgs/detail.html"
    plan_url_name = "organization-plans"

    organization: Organization

    def has_permission(self):
        if self.organization.is_public:
            return True
        else:
            return has_perm(self.request.user, Action.VIEW, self.organization)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["ancestors"] = self.organization.get_ancestors()
        context_data["page_title"] = build_page_title_context(
            organization=self.organization,
            language_code=self.request.LANGUAGE_CODE,
        )
        context_data["parent_links"].update({None: _("Informacija")})
        return context_data


class OrganizationMembersView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganizationBaseViewMixin,
    PlanMixin,
    ListView,
):
    template_name = "vitrina/orgs/members.html"
    context_object_name = "members"
    paginate_by = 20

    organization: Organization

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.organization,
        )

    def get_queryset(self):
        return Representative.objects.filter(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=self.organization.pk,
        ).order_by("role", "first_name", "last_name")

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["has_permission"] = has_perm(
            self.request.user,
            Action.CREATE,
            Representative,
            self.organization,
        )
        context_data["parent_links"].update({None: _("Tvarkytojai")})
        return context_data


class OrganizationContactsView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganizationBaseViewMixin,
    PlanMixin,
    ListView,
):
    template_name = "vitrina/orgs/contacts.html"
    context_object_name = "contacts"
    paginate_by = 9

    organization: Organization

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Contact,
            self.organization,
        )

    def get_queryset(self):
        return Contact.objects.filter(organization=self.organization).order_by("email")

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["has_permission"] = has_perm(
            self.request.user,
            Action.CREATE,
            Contact,
            self.organization,
        )
        context_data["parent_links"].update({None: _("Kontaktai")})
        return context_data


class ContactCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganizationBaseViewMixin,
    PlanMixin,
    CreateView,
):
    model = Contact
    form_class = ContactCreateForm
    template_name = "base_form.html"

    organization: Organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object_id"] = self.organization.pk
        return kwargs

    def get_success_url(self):
        return reverse("organization-contacts", kwargs={"pk": self.kwargs.get("pk")})

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Contact, self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contact_url"] = reverse("organization-contacts", args=[self.organization.pk])
        context["current_title"] = _("Kontakto pridėjimas")
        context["parent_links"].update(
            {
                self.get_success_url(): _("Kontaktai"),
                None: _("Pridėti"),
            }
        )
        return context

    def form_valid(self, form):
        contact = form.cleaned_data.get("contact")
        email = form.cleaned_data.get("email")
        phone = form.cleaned_data.get("phone")
        contact_name = form.cleaned_data.get("contact_name")
        position = form.cleaned_data.get("position")

        Contact.objects.create(
            organization=self.organization,
            contact_name=contact_name,
            content_type=ContentType.objects.get_for_model(contact) if contact else None,
            object_id=contact.pk if contact else None,
            email=email if email else contact.email,
            phone=phone if phone else contact.phone,
            position=position,
        )

        return HttpResponseRedirect(self.get_success_url())


class ContactUpdateView(LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, UpdateView):
    model = Contact
    form_class = ContactUpdateForm
    template_name = "base_form.html"
    pk_url_kwarg = "contact_id"

    organization: Organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object"] = self.organization
        return kwargs

    def has_permission(self):
        contact = get_object_or_404(Contact, pk=self.kwargs.get("contact_id"))
        return has_perm(self.request.user, Action.UPDATE, contact)

    def get_success_url(self):
        return reverse("organization-contacts", kwargs={"pk": self.kwargs.get("pk")})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["representative_url"] = reverse("organization-members", args=[self.organization.pk])
        context["current_title"] = _("Kontaktų redagavimas")
        context["parent_links"].update(
            {
                self.get_success_url(): _("Kontaktai"),
                None: _("Redaguoti"),
            }
        )
        return context

    def form_valid(self, form):
        contact = form.cleaned_data.get("contact")
        email = form.cleaned_data.get("email")
        phone = form.cleaned_data.get("phone")
        contact_name = form.cleaned_data.get("contact_name")
        position = form.cleaned_data.get("position")

        self.object.email = email or contact.email
        self.object.phone = phone or contact.phone
        self.object.object_id = contact.pk if contact else None
        self.object.contact_name = contact_name
        self.object.position = position
        self.object.content_type = ContentType.objects.get_for_model(contact) if contact else None
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class ContactDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Contact
    template_name = "confirm_delete.html"
    pk_url_kwarg = "contact_id"

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseRedirect | HttpResponseBase:
        self.object = self.get_object()

        is_contact_assigned_to_agreements = (
            self.object.agreements_as_assignee_representative.exists()
            or self.object.agreements_as_assigner_representative.exists()
        )

        if is_contact_assigned_to_agreements:
            messages.error(request, _("Šio kontakto ištrinti negalima, nes jis yra naudojamas sutartyse."))
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        contact = get_object_or_404(Contact, pk=self.kwargs.get("contact_id"))
        return has_perm(self.request.user, Action.DELETE, contact)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["delete_text"] = _('Ar tikrai norite ištrinti kontaktą "{contact}"?').format(contact=self.get_object())
        return context

    def get_success_url(self):
        return reverse("organization-contacts", kwargs={"pk": self.kwargs.get("pk")})


class OrganizationProjectsView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganizationBaseViewMixin,
    PlanMixin,
    ListView,
):
    template_name = "vitrina/orgs/projects_list.html"
    context_object_name = "projects"
    paginate_by = 9

    organization: Organization

    def has_permission(self):
        if self.organization.is_public:
            return True
        else:
            return has_perm(self.request.user, Action.VIEW, self.organization)

    def get_queryset(self):
        return get_projects(self.request.user, approved_only=False).filter(organization=self.organization)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["has_permission"] = has_perm(
            self.request.user,
            Action.UPDATE,
            self.organization,
        )
        context_data["parent_links"].update({None: _("Panaudojimo atvejai")})

        return context_data


class OrganizationBasedAgreementListView(OrganizationBaseViewMixin, PlanMixin, BaseAgreementListView):
    template_name = "vitrina/orgs/organization_agreements.html"
    parent_type = "organization"

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.parent: Organization = self.organization
        return None

    def has_permission(self) -> bool:
        return can_view_organization_agreements(self.request.user, self.organization)

    def get_queryset(self) -> QuerySet:
        return (
            get_agreements(self.request.user)
            .filter(assigner=self.organization)
            .annotate(
                priority=Case(
                    When(status=AgreementStatuses.SUBMITTED, then=0),
                    When(status=AgreementStatuses.APPROVED, then=1),
                    When(status=AgreementStatuses.INITIATED, then=2),
                    When(status=AgreementStatuses.ACTIVE, then=3),
                    When(status=AgreementStatuses.SIGNED, then=4),
                    When(status=AgreementStatuses.CREATED, then=5),
                    When(status=AgreementStatuses.FORMED, then=6),
                    When(status=AgreementStatuses.TERMINATED, then=7),
                    default=8,
                    output_field=IntegerField(),
                )
            )
            .order_by("priority", "created_at")
        )

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["parent_links"].update({None: _("Sutartys")})
        return context


class OrganizationBasedAgreementDetailView(OrganizationBaseViewMixin, BaseAgreementDetailView):
    template_name = "vitrina/orgs/organization_agreements_detail.html"
    parent_type = "organization"

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.parent: Organization = self.organization

    def get_agreement_queryset(self) -> QuerySet:
        return Agreement.objects.filter(assigner=self.organization)

    def has_permission(self) -> bool:
        return can_view_organization_agreement(self.request.user, self.agreement)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "can_create_agreements": False,  # Assignee action, assigner is not able to execute it.
                "can_submit_agreements": False,  # Assignee action, assigner is not able to execute it.
                "can_approve_agreements": can_approve_agreements(self.request.user, self.agreement),
                "can_form_agreements": can_form_agreements(self.request.user, self.agreement),
                "can_initiate_agreements": False,  # Assignee action, assigner is not able to execute it.
                "can_sign_agreements": can_sign_agreements(self.request.user, self.agreement),
                "can_upload_agreement_file": can_upload_agreement_file(self.request.user, self.agreement),
            }
        )
        context["parent_links"].update(
            {reverse("organization-agreement-list", args=[self.organization.pk]): _("Sutartys"), None: _("Sutartis")}
        )

        return context


class OrganizationBasedAgreementNegotiateMixin(OrganizationBaseViewMixin, AgreementNegotiateMixin):
    """Mixin class used for organization-based agreement status-change views"""

    template_name = "vitrina/orgs/organization_based_agreement_negotiate.html"

    def get_agreement_queryset(self) -> QuerySet:
        return Agreement.objects.filter(assigner=self.organization)

    def get_success_url(self) -> str:
        return reverse("organization-agreement-detail", args=[self.organization.pk, self.agreement.pk])

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_title": self.title,
                "agreement": self.agreement,
                "project": self.agreement.project,
                "datasets": self.agreement.project.datasets.filter(organization=self.agreement.assigner).all(),
            }
        )
        context["parent_links"].update(
            {
                reverse("organization-agreement-list", args=[self.organization.pk]): _("Sutartys"),
                reverse(
                    "organization-agreement-detail", args=[self.organization.pk, self.agreement.pk]
                ): self.agreement.detail_page_title,
                None: self.title,
            }
        )
        context.pop("tabs")

        return context


class OrganizationBasedAgreementApproveView(AgreementApproveMixin, OrganizationBasedAgreementNegotiateMixin):
    """Organization-based agreement form view responsible for moving the agreement to status `APPROVED`"""


class OrganizationBasedAgreementFormView(AgreementFormMixin, OrganizationBasedAgreementNegotiateMixin):
    """Organization-based agreement form view responsible for moving the agreement to status `FORMED`"""


class OrganizationBasedAgreementSignView(AgreementSignMixin, OrganizationBasedAgreementNegotiateMixin):
    """Organization-based agreement form view responsible for moving the agreement to status `SIGNED`"""


class OrganizationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationUpdateForm
    template_name = "base_form.html"
    view_url_name = "organization:edit"
    context_object_name = "organization"

    def has_permission(self):
        org = self.get_object()
        return has_perm(self.request.user, Action.UPDATE, org)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            org = get_object_or_404(Organization, id=self.kwargs["pk"])
            return redirect(org)

    def _is_wizard_request(self) -> bool:
        return bool(self.request.headers.get("X-Wizard-Request"))

    def get_template_names(self):
        if self._is_wizard_request():
            return ["vitrina/orgs/_wizard_org_fragment.html"]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Organizacijos redagavimas")
        context["page_title"] = build_page_title_context(organization=self.object)
        if self._is_wizard_request():
            form = context.get("form")
            if form and hasattr(form, "helper"):
                form.helper.form_tag = False
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        organization = self.get_object()
        kwargs["user"] = self.request.user
        if organization.jurisdiction_id:
            kwargs["initial"] = {"jurisdiction": organization.jurisdiction_id}
        return kwargs

    def get(self, request, *args, **kwargs):
        return super(OrganizationUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.slug = slugify(self.object.title)

        current_parent = self.object.get_parent()
        new_jurisdiction = form.cleaned_data.get("jurisdiction")

        self.object.save()

        if current_parent != new_jurisdiction and new_jurisdiction:
            Organization.fix_tree(fix_paths=True)
            parent_org = get_or_create_parent_org(new_jurisdiction)
            node = Organization.objects.get(pk=self.object.pk)
            node.move(parent_org, "sorted-child")
            self.object.refresh_from_db()

        if "jurisdiction" in form.changed_data:
            # save related datasets to update search index
            for dataset in self.object.dataset_set.all():
                dataset.save()

            # save related requests to update search index
            for request_assignment in self.object.requestassignment_set.all():
                request_assignment.request.save()

        messages.success(self.request, _("Organizacija atnaujinta sėkmingai"))

        if self._is_wizard_request():
            response = render(
                self.request,
                "vitrina/orgs/_wizard_org_fragment.html",
                self.get_context_data(form=form),
            )
            response["HX-Trigger"] = "treeRefresh"
            return response

        return HttpResponseRedirect(self.get_success_url())


class OrganizationCreateSearchView(TemplateView):
    template_name = "vitrina/orgs/organization_create_search.html"


class OrganizationCreateSearchUpdateView(TemplateView):
    template_name = "vitrina/orgs/organization_create_search_items.html"
    model_uri = "datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo"
    query_uri = 'ja_pavadinimas.contains("{}")'

    def get_context_data(self, **kwargs):
        q = self.request.GET.get("q")
        context = super().get_context_data(**kwargs)
        data = get_data_from_spinta(model=self.model_uri, query=self.query_uri.format(q)).get("_data", [])
        company_names = [data_item.get("ja_pavadinimas") for data_item in data]
        extra_context = {"company_names": company_names}
        context.update(extra_context)
        return context


class OrganizationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationCreateForm
    template_name = "vitrina/orgs/organization_form.html"
    view_url_name = "organization:create"
    context_object_name = "organization"
    model_uri = "datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo"
    query_uri = "ja_pavadinimas.contains('{}')"

    data: List
    spinta_errors: List

    def has_permission(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect("home")

    def dispatch(self, request, *args, **kwargs):
        q = request.GET.get("q")
        data = get_data_from_spinta(model=self.model_uri, query=self.query_uri.format(q))
        errors = data.get("errors", [])
        if errors:
            errors = [_("Nepavyko atnaujinti duomenų iš JAR:")] + errors
        self.spinta_errors = errors
        self.data = data.get("_data", [])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["spinta_errors"] = self.spinta_errors
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.data and len(self.data) == 1:
            initial_dict = {
                "title": self.data[0].get("ja_pavadinimas"),
                "company_code": self.data[0].get("ja_kodas"),
                "address": self.data[0].get("pilnas_adresas"),
            }
            kwargs["initial"] = initial_dict
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if jurisdiction := form.cleaned_data.get("jurisdiction"):
            parent_org: Organization = get_or_create_parent_org(jurisdiction)
            org: Organization = parent_org.add_child(
                title=form.cleaned_data.get("title"),
                name=form.cleaned_data.get("name"),
                image=form.cleaned_data.get("image"),
                company_code=form.cleaned_data.get("company_code"),
                address=form.cleaned_data.get("address"),
                email=form.cleaned_data.get("email"),
                phone=form.cleaned_data.get("phone"),
                description=form.cleaned_data.get("description"),
                kind=form.cleaned_data.get("kind"),
                publisher=False,
                is_public=True,
                jurisdiction=jurisdiction,
            )
            # this is needed to update organization parent
            org: Organization = Organization.objects.get(pk=org.pk)
            org.refresh_from_db()
        else:
            org: Organization = Organization.add_root(
                title=form.cleaned_data.get("title"),
                name=form.cleaned_data.get("name"),
                image=form.cleaned_data.get("image"),
                company_code=form.cleaned_data.get("company_code"),
                address=form.cleaned_data.get("address"),
                email=form.cleaned_data.get("email"),
                phone=form.cleaned_data.get("phone"),
                description=form.cleaned_data.get("description"),
                kind=form.cleaned_data.get("kind"),
                publisher=False,
                is_public=True,
            )
        Organization.fix_tree(fix_paths=True)
        return HttpResponseRedirect(self.get_success_url(org))

    def get_success_url(self, organization):
        return reverse("organization-detail", kwargs={"pk": organization.pk})


DATASET_REPRESENTATIVE_CREATE_EMAIL_IDENTIFIER = "auth-org-representative-without-credentials"
ORGANIZATION_REPRESENTATIVE_CREATE_EMAIL_IDENTIFIER = "organization-member-add"


class RepresentativeCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganizationBaseViewMixin,
    PlanMixin,
    CreateView,
):
    model = Representative
    form_class = RepresentativeCreateForm
    template_name = "base_form.html"

    organization: Organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object"] = self.organization
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("organization-members", kwargs={"pk": self.kwargs.get("pk")})

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Representative, self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["representative_url"] = reverse("organization-members", args=[self.organization.pk])
        context["current_title"] = _("Tvarkytojo pridėjimas")
        context["parent_links"].update(
            {reverse("organization-members", args=[self.organization.pk]): _("Tvarkytojai"), None: _("Pridėti")}
        )
        return context

    def form_valid(self, form):
        self.object: Representative = form.save(commit=False)
        self.object.object_id = self.organization.pk
        self.object.content_type = ContentType.objects.get_for_model(self.organization)
        subscribe = form.cleaned_data.get("subscribe")
        try:
            user = User.objects.get(email=self.object.email)
            if self.object.role in Representative.COORDINATOR_ROLES:
                user.organization = self.organization
                user.save()
        except ObjectDoesNotExist:
            user = None
        try:
            organization = Organization.objects.get(email=self.object.email)
        except ObjectDoesNotExist:
            organization = None

        if user:
            self.object.user = user
            self.object.save()
            if not user.organization:
                user.organization = self.organization
                user.save()
            link = "%s%s" % (
                get_current_domain(self.request),
                reverse("organization-detail", kwargs={"pk": self.object.object_id}),
            )
            manage_subscriptions_for_representative(subscribe, user, self.organization, link)
        elif organization:
            if self.object.role in Representative.COORDINATOR_ROLES:
                form.add_error("role", _("Organizacijai gali būti suteikta tik tvarkytojo rolė"))
                return self.form_invalid(form)
            self.object.organization = organization
            self.object.save()

            if not organization.publisher:
                organization.publisher = True
                organization.save()
        else:
            if not SentMail.objects.filter(
                Q(
                    Q(identifier=DATASET_REPRESENTATIVE_CREATE_EMAIL_IDENTIFIER)
                    | Q(identifier=ORGANIZATION_REPRESENTATIVE_CREATE_EMAIL_IDENTIFIER)
                )
                & Q(recipient=f"['{self.object.email}']")
            ):
                self.object.save()
                serializer = URLSafeSerializer(settings.SECRET_KEY)
                token = serializer.dumps({"representative_id": self.object.pk, "subscribe": subscribe})
                url = "%s%s" % (
                    get_current_domain(self.request),
                    reverse("representative-register", kwargs={"token": token}),
                )

                email(
                    [self.object.email],
                    ORGANIZATION_REPRESENTATIVE_CREATE_EMAIL_IDENTIFIER,
                    "vitrina/emails/request_for_organization_member_add.md",
                    {"organization": self.organization.title, "link": url},
                )

                messages.info(self.request, _("Naudotojui išsiųstas laiškas dėl registracijos"))
        self.object.save()

        if self.object.has_api_access:
            api_key = secrets.token_urlsafe()
            ApiKey.objects.create(api_key=hash_api_key(api_key), enabled=True, representative=self.object)
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            api_key = serializer.dumps({"api_key": api_key})
            return HttpResponseRedirect(
                reverse(
                    "representative-api-key",
                    args=[self.organization.pk, self.object.pk, api_key],
                )
            )

        phone = form.cleaned_data.get("phone")
        if phone:
            self.object.phone = phone
            self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class RepresentativeUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, UpdateView
):
    model = Representative
    form_class = RepresentativeUpdateForm
    template_name = "base_form.html"
    pk_url_kwarg = "representative_id"

    organization: Organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object"] = self.organization
        kwargs["user"] = self.request.user
        return kwargs

    def has_permission(self):
        representative = get_object_or_404(Representative, pk=self.kwargs.get("representative_id"))
        return has_perm(self.request.user, Action.UPDATE, representative)

    def get_success_url(self):
        return reverse("organization-members", kwargs={"pk": self.kwargs.get("pk")})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["representative_url"] = reverse("organization-members", args=[self.organization.pk])
        context["current_title"] = _("Tvarkytojo redagavimas")
        context["parent_links"].update(
            {reverse("organization-members", args=[self.organization.pk]): _("Tvarkytojai"), None: _("Redaguoti")}
        )
        return context

    def form_valid(self, form):
        self.object: Representative = form.save()
        subscribe = form.cleaned_data.get("subscribe")

        if self.object.user and not self.object.user.organization:
            self.object.user.organization = self.organization
            self.object.user.save()
        link = "%s%s" % (
            get_current_domain(self.request),
            reverse("organization-detail", kwargs={"pk": self.organization.pk}),
        )
        manage_subscriptions_for_representative(subscribe, self.object.user, self.organization, link)
        if self.object.has_api_access:
            if not self.object.apikey_set.exists():
                api_key = secrets.token_urlsafe()
                ApiKey.objects.create(
                    api_key=hash_api_key(api_key),
                    enabled=True,
                    representative=self.object,
                )

                serializer = URLSafeSerializer(settings.SECRET_KEY)
                api_key = serializer.dumps({"api_key": api_key})
                return HttpResponseRedirect(
                    reverse(
                        "representative-api-key",
                        args=[self.organization.pk, self.object.pk, api_key],
                    )
                )
            elif form.cleaned_data.get("regenerate_api_key"):
                api_key = secrets.token_urlsafe()
                api_key_obj = self.object.apikey_set.first()
                api_key_obj.api_key = hash_api_key(api_key)
                api_key_obj.enabled = True
                api_key_obj.save()

                serializer = URLSafeSerializer(settings.SECRET_KEY)
                api_key = serializer.dumps({"api_key": api_key})
                return HttpResponseRedirect(
                    reverse(
                        "representative-api-key",
                        args=[self.organization.pk, self.object.pk, api_key],
                    )
                )
        else:
            self.object.apikey_set.all().delete()

        phone = form.cleaned_data.get("phone")
        if phone:
            self.object.phone = phone
        return HttpResponseRedirect(self.get_success_url())


class RepresentativeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Representative
    template_name = "confirm_delete.html"

    def has_permission(self):
        representative = get_object_or_404(Representative, pk=self.kwargs.get("pk"))
        return has_perm(self.request.user, Action.DELETE, representative)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        role = (
            "koordinatorių"
            if obj.role in Representative.COORDINATOR_ROLES
            else "tvarkytojų"
            if obj.organization
            else "tvarkytoją"
        )
        context["delete_text"] = (
            _(f'Ar tikrai norite pašalinti "{obj.organization.title}" iš {role}?')
            if obj.organization
            else _(f'Ar tikrai norite ištrinti "{obj}" {role}?')
        )
        return context

    def get_success_url(self):
        return reverse("organization-members", kwargs={"pk": self.kwargs.get("organization_id")})

    def form_valid(self, form: BaseForm) -> HttpResponse:
        if self.object.organization and (organization_id := self.kwargs.get("organization_id")):
            Dataset.objects.filter(
                organization_id=organization_id,
                publisher__isnull=False,
            ).update(publisher=None)

        pre_representative_delete(self.object)
        return super().form_valid(form)


class RepresentativeRegisterView(RegisterView):
    form_class = RepresentativeRegisterForm
    data: dict
    representative: Representative

    def dispatch(self, request, *args, **kwargs):
        token = self.kwargs.get("token")
        serializer = URLSafeSerializer(settings.SECRET_KEY)
        try:
            self.data = serializer.loads(token)
        except BadSignature:
            return redirect("register-link-expired")

        self.representative = Representative.objects.filter(pk=self.data.get("representative_id")).first()
        if not self.representative or self.representative.user:
            return redirect("register-link-expired")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["representative"] = self.representative
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.form_class(self.representative, request.POST)
        if form.is_valid():
            user = form.save()

            EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
            user.status = User.ACTIVE
            user.save()

            subscribe = self.data.get("subscribe")
            try:
                representative = Representative.objects.get(pk=self.data.get("representative_id"))
            except ObjectDoesNotExist:
                representative = None
            if representative:
                representative.user = user
                representative.save()

                if isinstance(representative.content_object, Organization):
                    user.organization = representative.content_object
                    user.save()

                    link = "%s%s" % (
                        get_current_domain(self.request),
                        reverse(
                            "organization-detail",
                            kwargs={"pk": representative.content_object.pk},
                        ),
                    )
                    manage_subscriptions_for_representative(subscribe, user, representative.content_object, link)

                elif isinstance(representative.content_object, Dataset):
                    user.organization = representative.content_object.organization
                    user.save()

                    link = "%s%s" % (
                        get_current_domain(self.request),
                        reverse(
                            "dataset-detail",
                            kwargs={"pk": representative.content_object.pk},
                        ),
                    )
                    manage_dataset_subscriptions(subscribe, user, representative.content_object, link)

            # update related representatives
            if reps := Representative.objects.filter(email=user.email, user__isnull=True):
                reps.update(user=user)

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("home")
        return render(request=request, template_name=self.template_name, context={"form": form})


class RepresentativeRegisterExpiredView(TemplateView):
    template_name = "vitrina/orgs/register_link_expired.html"


class PartnerRegisterInfoView(TemplateView):
    template_name = "vitrina/orgs/partners/register.html"


class PartnerRegisterView(CreateView):
    form_class = PartnerRegisterForm
    template_name = "vitrina/orgs/partners/register_form.html"
    jar_model_uri = "datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo"
    jar_query_uri = "ja_kodas={}"
    base_template_content = """
        Portale pateiktas naujas koordinatoriaus prašymas.\n
        {0}
    """
    email_identifier = "coordinator-request-created"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_viisp_login:
            messages.error(
                self.request, _("Norėdami registruoti naują duomenų teikėją, privalote prisijungti su VIISP.")
            )
            return redirect("viisp-login")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        org = form.cleaned_data.get("organization")
        if org and not isinstance(org, Organization):
            org_data = get_data_from_spinta(model=self.jar_model_uri, query=self.jar_query_uri.format(org)).get(
                "_data"
            )[0]
            org = Organization.add_root(
                title=org_data.get("ja_pavadinimas"),
                address=org_data.get("pilnas_adresas"),
                company_code=org_data.get("ja_kodas"),
                provider=True,
                is_public=True,
            )

        representative_already_exists = Representative.objects.filter(
            user=self.request.user,
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=org.id,
        ).first()
        representative_request_already_exists = RepresentativeRequest.objects.filter(
            user=self.request.user,
            organization=org,
            status=RepresentativeRequest.CREATED,
        )
        if representative_already_exists:
            return redirect("representative-exists")
        elif representative_request_already_exists:
            return redirect("representative-request-exists")
        else:
            representative_request = RepresentativeRequest(
                user=self.request.user,
                organization=org,
                document=form.cleaned_data.get("request_form"),
                email=self.request.user.email,
                phone=form.cleaned_data.get("coordinator_phone_number"),
            )
            representative_request.save()
            supervisors = Representative.objects.filter(role=Representative.SUPERVISOR)
            for supervisor in supervisors:
                task = Task.objects.create(
                    title="Naujo duomenų teikėjo: {} prašymas".format(org.company_code),
                    description=f"Portale pateiktas naujas duomenų teikėjo prašymas: {org.company_code}.",
                    organization=org,
                    user=supervisor.user,
                    status=Task.CREATED,
                    type=Task.REQUEST,
                    content_type=ContentType.objects.get_for_model(Organization),
                    object_id=org.pk,
                )
                task.save()
            url = "{}/coordinator-admin/vitrina_orgs/representativerequest/".format(get_current_domain(self.request))
            email_data = prepare_email_by_identifier(
                self.email_identifier,
                self.base_template_content,
                "Portale pateiktas naujas koordinatoriaus prašymas",
                [url],
            )
            send_email_with_logging(email_data, [s.email for s in supervisors])
        return redirect(reverse("partner-register-complete"))


class PartnerRegisterCompleteView(TemplateView):
    template_name = "vitrina/orgs/partners/register_complete.html"


class OrganizationPlanView(PermissionRequiredMixin, PlanMixin, OrganizationBaseViewMixin, TemplateView):
    template_name = "vitrina/orgs/plans.html"
    plan_url_name = "organization-plans"

    organization: Organization

    def has_permission(self):
        if self.organization.is_public:
            return True
        else:
            return has_perm(self.request.user, Action.VIEW, self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", "opened")
        if status == "closed":
            context["plans"] = self.organization.receiver_plans.filter(is_closed=True)
        else:
            context["plans"] = self.organization.receiver_plans.filter(is_closed=False)
        context["can_manage_plans"] = has_perm(self.request.user, Action.PLAN, self.organization)
        context["history_url"] = reverse("organization-plans-history", args=[self.organization.pk])
        context["history_url_name"] = "organization-plans-hisotry"
        context["can_manage_history"] = has_perm(
            self.request.user,
            Action.HISTORY_VIEW,
            self.organization,
        )
        context["selected_tab"] = status
        context["parent_links"].update({None: _("Planas")})
        return context

    def get_plan_object(self):
        return self.organization


class OrganizationPlanCreateView(PermissionRequiredMixin, OrganizationBaseViewMixin, CreateView):
    model = Plan
    form_class = OrganizationPlanForm
    template_name = "vitrina/plans/form.html"

    organization: Organization

    def has_permission(self):
        return has_perm(self.request.user, Action.PLAN, self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Naujas terminas")
        context["parent_links"].update(
            {reverse("organization-plans", args=[self.organization.pk]): _("Planas"), None: _("Pridėti")}
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["organizations"] = [self.organization]
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.receiver = self.organization
        self.object.save()
        return redirect(reverse("organization-plans", args=[self.organization.pk]))


class OrganizationApiKeysView(
    LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, TemplateView
):
    template_name = "vitrina/orgs/apikeys.html"

    organization: Organization

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        key_client_ids = []
        msg = None
        error = False
        err_message = ""
        delete_error = False

        storage = messages.get_messages(self.request)
        if len(storage._loaded_messages) == 1:
            if storage._loaded_messages[0].level == 20:
                msg = storage._loaded_messages[0]
                del storage._loaded_messages[0]
            elif storage._loaded_messages[0].level == 40:
                delete_error = True
                del storage._loaded_messages[0]

        try:
            response = get_auth_session().get(SPINTA_SERVER_URL + "/auth/clients")
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error retrieving keys: {e}"
        else:
            try:
                keys = response.json()
            except JSONDecodeError as e:
                err_message = f"Error decoding JSON: {e}"

            if response.status_code == 200:
                for key in keys:
                    client_id = key.get("client_id")
                    client_name = key.get("client_name")
                    org = Organization.objects.filter(name=client_name).first()
                    key_client_ids.append(client_id)

                    if not ApiKey.objects.filter(client_id=client_id).exists():
                        ApiKey.objects.create(
                            client_id=client_id,
                            client_name=client_name,
                            organization=org,
                            enabled=True,
                        )
                keys_in_database = ApiKey.objects.filter(client_id__isnull=False)

                for key in keys_in_database:
                    if key.client_id not in key_client_ids:
                        key.enabled = False
                        key.save()
            else:
                error = True
                err_message = "Error syncing apikeys"

        if error:
            logger.warning(err_message)
            context_data["api_error"] = _(
                "Nepavyko susisiekti su Saugyklos API, todėl raktai rodomi lentelėje gali nesutapti"
                + " su raktais Saugykloje."
            )

        if delete_error:
            context_data["delete_error"] = _("API rakto pašalinimas nesėkmingas.")

        context_data["parent_links"].update(
            {
                None: _("Raktai"),
            }
        )
        context_data["can_manage_keys"] = has_perm(self.request.user, Action.MANAGE_KEYS, self.organization)
        if msg:
            context_data["success_message"] = msg
        internal = ApiKey.objects.filter(organization=self.organization)
        scopes = ApiScope.objects.filter(organization=self.organization).values_list("key_id", flat=True)
        external = ApiKey.objects.filter(pk__in=scopes).exclude(pk__in=internal)
        project_ids = Project.objects.filter(datasets__organization=self.organization).values_list("pk", flat=True)
        project_keys = ApiKey.objects.filter(project_id__in=project_ids)
        context_data["internal_keys"] = internal
        context_data["external_keys"] = external | project_keys
        return context_data


class OrganizationApiKeysDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, TemplateView
):
    template_name = "vitrina/orgs/apikeys_detail.html"
    pk_url_kwarg = "apikey_id"

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.api_key = get_object_or_404(ApiKey, pk=kwargs["apikey_id"])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["parent_links"].update(
            {reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"), None: _("Raktas")}
        )
        api_key = ApiKey.objects.filter(pk=self.api_key.pk).get()
        context_data["key"] = api_key

        prefix = "spinta"
        suffixes = [
            "_getone",
            "_getall",
            "_search",
            "_changes",
            "_insert",
            "_upsert",
            "_update",
            "_patch",
            "_delete",
            "_wipe",
        ]
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]

        grouped = {}
        scopes_final = {}
        scopes = ApiScope.objects.filter(key=api_key)

        for scope in scopes:
            if scope.scope == "spinta_set_meta_fields":
                grouped.setdefault("set_meta_fields", [])
                grouped["set_meta_fields"].append(scope)
            if any((match := ext) in scope.scope for ext in suffixes):
                code = scope.scope.removeprefix(prefix).removesuffix(match)
                if len(code) > 0:
                    code = code.removeprefix("_datasets_gov_")
                    if code.startswith("_"):
                        code = code.removeprefix("_")
                else:
                    code = "(viskas)"
                grouped.setdefault(code, [])
                grouped[code].append(scope)

        for k, v in grouped.items():
            dt = {
                "read": False,
                "write": False,
                "wipe": False,
                "title": "",
                "url": None,
                "enabled": False,
            }
            if k == "set_meta_fields":
                dt.update({"title": "set_meta_fields"})
                for s in v:
                    if s.enabled:
                        dt.update({"enabled": True})
                scopes_final[k] = dt
            else:
                dt.update({"title": k})
                for s in v:
                    if any(sc in s.scope for sc in read):
                        dt.update({"read": True})
                    if any(sc in s.scope for sc in write):
                        dt.update({"write": True})
                    if "wipe" in s.scope:
                        dt.update({"wipe": True})
                    dt.update({"enabled": s.enabled})
            if k != "set_meta_fields" and k != "(viskas)":
                org = Organization.objects.filter(name=k)
                target_dataset = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Dataset), name=k
                )
                if org:
                    ct = ContentType.objects.get_for_model(org.get())
                    dt.update(
                        {
                            "title": org.get().title,
                            "url": org.get().get_absolute_url,
                            "obj": org.get(),
                            "ct": ct,
                        }
                    )
                if target_dataset:
                    ct = ContentType.objects.get_for_model(Dataset)
                    dataset = Dataset.objects.get(pk=target_dataset.get().dataset_id)
                    dt.update(
                        {
                            "title": dataset.title,
                            "url": dataset.get_absolute_url,
                            "obj": dataset,
                            "ct": ct,
                        }
                    )
            scopes_final[k] = dt
        context_data["scopes"] = scopes_final
        return context_data


class OrganizationApiKeysCreateView(PermissionRequiredMixin, OrganizationBaseViewMixin, CreateView):
    model = ApiKey
    form_class = ApiKeyForm
    template_name = "base_form.html"

    organization: Organization

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Naujas raktas")
        context["parent_links"].update(
            {reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"), None: _("Pridėti")}
        )
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.organization = self.organization
        permissions = [
            "spinta_set_meta_fields",
            "spinta_getone",
            "spinta_getall",
            "spinta_search",
            "spinta_changes",
        ]
        api_key = secrets.token_urlsafe()
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"secret": api_key, "scopes": permissions}
        error = False
        err_message = ""
        try:
            response = get_auth_session().post(SPINTA_SERVER_URL + "/auth/clients", json=data, headers=headers)
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error creating apikey: {e}."
        else:
            if response.status_code == 200:
                if "client_id" in response.json() and "client_name" in response.json():
                    self.object.client_id = response.json()["client_id"]
                    self.object.client_name = response.json()["client_name"]
                    self.object.api_key = hash_api_key(api_key)
                    self.object.enabled = True
                    self.object.save()
                    for p in permissions:
                        ApiScope.objects.create(
                            key=self.object,
                            organization=self.organization,
                            scope=p,
                            enabled=True,
                        )
                    messages.info(
                        self.request,
                        _("API raktas rodomas tik vieną kartą, todėl būtina nusikopijuoti. Sukurtas raktas:" + api_key),
                    )
            else:
                error = True
                err_message = "Unable to create scopes for apikey"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(reverse("organization-apikeys", args=[self.organization.pk]))


class OrganizationApiKeysUpdateView(PermissionRequiredMixin, UpdateView):
    model = ApiKey
    form_class = ApiKeyForm
    template_name = "base_form.html"
    pk_url_kwarg = "apikey_id"

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get("apikey_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prefix = "spinta"
        suffixes = [
            "_getone",
            "_getall",
            "_search",
            "_changes",
            "_insert",
            "_upsert",
            "_update",
            "_patch",
            "_delete",
            "_wipe",
        ]
        if self.api_key.client_id:
            error = False
            err_message = ""
            try:
                response = get_auth_session().get(SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id)
            except requests.exceptions.RequestException as e:
                error = True
                err_message = f"Error updating key with client_id: {self.api_key.client_id}, {e}"
            else:
                if response.status_code == 200:
                    if "scopes" in response.json():
                        scopes = response.json()["scopes"]

                        existing = ApiScope.objects.filter(key=self.api_key)
                        for ex in existing:
                            ex.delete()

                        for scope in scopes:
                            org = None
                            if any((match := ext) in scope for ext in suffixes):
                                code = scope.removeprefix(prefix).removesuffix(match)
                                if code:
                                    org = Organization.objects.filter(name=code.removeprefix("_datasets_gov_")).first()
                            if scope != "spinta_set_meta_fields":
                                ApiScope.objects.create(
                                    key=self.api_key,
                                    scope=scope,
                                    enabled=True,
                                    organization=org,
                                    dataset=None,
                                )
                else:
                    error = True
                    err_message = f"Unable to create scopes for apikey with client_id {self.api_key.client_id}"
            if error:
                logger.warning(err_message)
                messages.error(self.request, _("Saugant API raktą įvyko klaida."))

        context["current_title"] = _("Rakto redagavimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"client_name": self.object.client_name}
        error = False
        err_message = ""
        try:
            response = get_auth_session().patch(
                SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error updating apikey with client_id: {self.api_key.client_id}, {e}"
        else:
            if response.status_code == 200:
                self.object.save()
            else:
                error = True
                err_message = f"Error updating apikey with client_id: {self.api_key.client_id}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(reverse("organization-apikeys", args=[self.organization.pk]))


class OrganizationApiKeysRegenerateView(PermissionRequiredMixin, UpdateView):
    model = ApiKey
    form_class = ApiKeyRegenerateForm
    template_name = "base_form.html"
    pk_url_kwarg = "apikey_id"

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.apikey = get_object_or_404(ApiKey, pk=kwargs.get("apikey_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Rakto slaptažodžio keitimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.api_key = hash_api_key(form.cleaned_data.get("new_key"))
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"secret": form.cleaned_data.get("new_key")}
        error = False
        err_message = ""
        try:
            response = get_auth_session().post(
                SPINTA_SERVER_URL + "/auth/clients/" + self.apikey.client_name,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error regenerating apikey with client_name: {self.apikey.client_name}, {e}"
        else:
            if response.status_code == 200:
                self.object.save()
            else:
                error = True
                err_message = f"Error regenerating apikey with client_name: {self.apikey.client_name}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(reverse("organization-apikeys", args=[self.organization.pk]))


class OrganizationApiKeysDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ApiKey
    template_name = "confirm_delete.html"
    pk_url_kwarg = "apikey_id"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.apikey = get_object_or_404(ApiKey, pk=self.kwargs.get("apikey_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    @staticmethod
    def spinta_delete_apikey(client_id: str) -> Response:
        response = get_auth_session().delete(SPINTA_SERVER_URL + "/auth/clients/" + client_id)

        return response

    def form_valid(self, form: BaseForm) -> HttpResponse:
        try:
            response = self.spinta_delete_apikey(self.apikey.client_id)
            if response.status_code == 204:
                return super().form_valid(form)
        except requests.exceptions.RequestException:
            pass

        messages.error(self.request, _("API rakto pašalinti nepavyko."))
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["api_key"] = self.apikey
        context["current_title"] = _("Šalinti raktą")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.apikey.pk],
            ): self.apikey.client_id,
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def get_success_url(self):
        return reverse("organization-apikeys", kwargs={"pk": self.kwargs.get("pk")})


class OrganizationApiKeysScopeCreateView(PermissionRequiredMixin, FormView):
    form_class = ApiScopeForm
    template_name = "base_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get("apikey_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["api_key"] = self.api_key
        kwargs["scope"] = None
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["api_key"] = self.api_key
        context["current_title"] = _("Nauja taikymo sritis")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            ): self.api_key,
        }
        return context

    def form_valid(self, form):
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]

        organization = None
        dataset = None

        scope_name = form.cleaned_data.get("scope")
        if scope_name == "spinta_set_meta_fields" or scope_name == "set_meta_fields":
            organization = self.organization
            ApiScope.objects.create(
                key=self.api_key,
                scope=scope_name,
                organization=organization,
                enabled=True,
            )
        else:
            target_org = Organization.objects.filter(name=scope_name)
            metadata = Metadata.objects.filter(content_type=ContentType.objects.get_for_model(Dataset), name=scope_name)
            if target_org.exists():
                if target_org.get().pk != self.organization.pk:
                    organization = target_org.get()
                    url = f"{get_current_domain(self.request)}{self.api_key.get_absolute_url()}"
                    rep_emails = Representative.objects.filter(
                        content_type=ContentType.objects.get_for_model(organization),
                        object_id=organization.pk,
                    ).values_list("email", flat=True)
                    email(
                        [rep_emails],
                        "apikey-request",
                        "vitrina/orgs/emails/request_for_data.md",
                        {"api_key": self.api_key, "url": url},
                    )
                    Task.objects.create(
                        content_type=ContentType.objects.get_for_model(ApiKey),
                        object_id=self.api_key.pk,
                        organization=target_org.get(),
                        title=f"Prašymas suteikti prieigą prie duomenų. Raktas: {self.api_key.pk}",
                        status=Task.CREATED,
                        type=Task.APIKEY,
                        description="Kita organizacija prašo suteikti prieigą prie duomenų raktui.",
                    )
            else:
                organization = self.organization
            if metadata.exists():
                dataset = Dataset.objects.filter(pk=metadata.get().dataset.pk).first()

        scope_list = []
        if form.cleaned_data.get("read"):
            for s in read:
                sc = "spinta_" + scope_name + s
                ApiScope.objects.create(
                    scope=sc,
                    organization=organization,
                    dataset=dataset,
                    key=self.api_key,
                    enabled=True,
                )
                scope_list.append(sc)
        if form.cleaned_data.get("write"):
            for s in write:
                sc = "spinta_" + scope_name + s
                ApiScope.objects.create(
                    scope=sc,
                    organization=organization,
                    dataset=dataset,
                    key=self.api_key,
                    enabled=True,
                )
                scope_list.append(sc)
        if form.cleaned_data.get("remove"):
            sc = "spinta_" + scope_name + "_wipe"
            ApiScope.objects.create(
                scope=sc,
                organization=organization,
                dataset=dataset,
                key=self.api_key,
                enabled=True,
            )
            scope_list.append(sc)

        existing = ApiScope.objects.filter(key=self.api_key).values_list("scope", flat=True)

        for new in scope_list:
            if new not in existing:
                existing.append(new)

        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"scopes": list(existing)}
        error = False
        err_message = ""
        try:
            response = get_auth_session().patch(
                SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error adding scope for apikey with client_id: {self.api_key.client_id}, {e}"
        else:
            if response.status_code != 200:
                error = True
                err_message = f"Error adding scope for apikey with client_id: {self.api_key.client_id}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            )
        )


class OrganizationApiKeysScopeChangeView(PermissionRequiredMixin, FormView):
    form_class = ApiScopeForm
    template_name = "base_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get("apikey_id"))
        self.name = kwargs.get("scope")
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["api_key"] = self.api_key
        kwargs["scope"] = self.name
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["api_key"] = self.api_key
        context["current_title"] = _("Taikymo srities redagavimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            ): self.api_key.client_id,
        }
        return context

    def form_valid(self, form):
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]
        create_read = False
        create_write = False
        create_wipe = False

        if self.name != "set_meta_fields" and self.name != "spinta_set_meta_fields":
            scopes = ApiScope.objects.filter(key=self.api_key).exclude(scope__icontains="datasets_gov")
            for sc in scopes:
                if not sc.scope == "spinta_set_meta_fields" or not sc.scope == "set_meta_fields":
                    if form.cleaned_data.get("read"):
                        if not any(s in sc.scope for s in read):
                            create_read = True
                    else:
                        for s in read:
                            scopes.filter(scope__icontains=s).delete()
                    if form.cleaned_data.get("write"):
                        if not any(s in sc.scope for s in write):
                            create_write = True
                    else:
                        for s in write:
                            scopes.filter(scope__icontains=s).delete()
                    if form.cleaned_data.get("remove"):
                        if "wipe" not in sc.scope:
                            create_wipe = True
                    else:
                        scopes.filter(scope__icontains="_wipe").delete()
            if create_read:
                for s in read:
                    ApiScope.objects.create(
                        key=self.api_key,
                        scope="spinta" + s,
                        organization=self.organization,
                        enabled=True,
                    )
            if create_write:
                for s in write:
                    ApiScope.objects.create(
                        key=self.api_key,
                        scope="spinta" + s,
                        organization=self.organization,
                        enabled=True,
                    )
            if create_wipe:
                ApiScope.objects.create(
                    key=self.api_key,
                    scope="spinta_wipe",
                    organization=self.organization,
                    enabled=True,
                )
            existing = ApiScope.objects.filter(key=self.api_key).values_list("scope", flat=True)
            headers = {"Content-Type": "application/json; charset=utf-8"}
            data = {"scopes": list(existing)}
            error = False
            err_message = ""
            try:
                response = get_auth_session().patch(
                    SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                    json=data,
                    headers=headers,
                )
            except requests.exceptions.RequestException as e:
                error = True
                err_message = f"Error updating scopes for apikey with client_id: {self.api_key.client_id}, {e}"
            else:
                if response.status_code != 200:
                    error = True
                    err_message = f"Error updating scopes for apikey with client_id: {self.api_key.client_id}"
            if error:
                logger.warning(err_message)
                messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(
            (
                reverse(
                    "organization-apikeys-detail",
                    args=[self.organization.pk, self.api_key.pk],
                )
            )
        )


class OrganizationApiKeysScopeObjectChangeView(PermissionRequiredMixin, FormView):
    form_class = ApiScopeForm
    template_name = "base_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get("apikey_id"))
        self.ct = get_object_or_404(ContentType, pk=kwargs.get("content_type_id"))
        self.object = get_object_or_404(self.ct.model_class(), pk=kwargs.get("obj_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["api_key"] = self.api_key
        kwargs["scope"] = self.object.name
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["api_key"] = self.api_key
        context["current_title"] = _("Taikymo srities redagavimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            ): self.api_key.client_id,
        }
        return context

    def form_valid(self, form):
        read = ["_getone", "_getall", "_search"]
        write = ["_insert", "_upsert", "_update", "_patch", "_delete"]
        create_read = False
        create_write = False
        create_wipe = False

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
            if form.cleaned_data.get("read"):
                if not any(s in sc.scope for s in read):
                    create_read = True
            else:
                for s in read:
                    scopes.filter(scope__icontains=s).delete()
            if form.cleaned_data.get("write"):
                if not any(s in sc.scope for s in write):
                    create_write = True
            else:
                for s in write:
                    scopes.filter(scope__icontains=s).delete()
            if form.cleaned_data.get("remove"):
                if "wipe" not in sc.scope:
                    create_wipe = True
            else:
                scopes.filter(scope__icontains="_wipe").delete()

        if len(scopes) == 0:
            if form.cleaned_data.get("read"):
                create_read = True
            if form.cleaned_data.get("write"):
                create_write = True
            if form.cleaned_data.get("remove"):
                create_wipe = True

        if create_read:
            for s in read:
                ApiScope.objects.create(
                    key=self.api_key,
                    scope="spinta_datasets_gov_" + scope_name + s,
                    organization=organization,
                    dataset=dataset,
                    enabled=True,
                )
        if create_write:
            for s in write:
                ApiScope.objects.create(
                    key=self.api_key,
                    scope="spinta_datasets_gov_" + scope_name + s,
                    organization=organization,
                    dataset=dataset,
                    enabled=True,
                )
        if create_wipe:
            ApiScope.objects.create(
                key=self.api_key,
                scope="spinta_datasets_gov_" + scope_name + "_wipe",
                organization=organization,
                dataset=dataset,
                enabled=True,
            )
        existing = ApiScope.objects.filter(key=self.api_key).values_list("scope", flat=True)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"scopes": list(existing)}
        error = False
        err_message = ""
        try:
            response = get_auth_session().patch(
                SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error updating scope for apikey with client_id: {self.api_key.client_id}, {e}"
        else:
            if response.status_code != 200:
                error = True
                err_message = f"Error updating scope for apikey with client_id: {self.api_key.client_id}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(
            (
                reverse(
                    "organization-apikeys-detail",
                    args=[self.organization.pk, self.api_key.pk],
                )
            )
        )


class OrganizationApiKeysScopeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    model = ApiScope
    template_name = "confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get("apikey_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Šalinti taikymo sritį")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            ): self.api_key,
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def post(self, request, *args, **kwargs):
        scope_name = kwargs.get("scope")
        api_key = kwargs.get("apikey_id")
        if scope_name == "spinta_set_meta_fields" or scope_name == "set_meta_fields":
            scopes = ApiScope.objects.filter(key_id=api_key, scope__contains="set_meta_fields")
            for scope in scopes:
                scope.delete()
        elif scope_name == "(viskas)":
            scopes = ApiScope.objects.filter(
                Q(key_id=api_key)
                & (
                    Q(scope="spinta_getone")
                    | Q(scope="spinta_getall")
                    | Q(scope="spinta_search")
                    | Q(scope="spinta_changes")
                )
            )
            for scope in scopes:
                scope.delete()

        existing = ApiScope.objects.filter(key=self.api_key).values_list("scope", flat=True)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"scopes": list(existing)}
        error = False
        err_message = ""
        try:
            response = get_auth_session().patch(
                SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error updating scopes for apikey with client_id {self.api_key.client_id}, {e}"
        else:
            if response.status_code != 200:
                error = True
                err_message = f"Error updating scopes for apikey with client_id {self.api_key.client_id}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            )
        )


class OrganizationApiKeysScopeObjectDeleteView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    model = ApiScope
    template_name = "confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=kwargs.get("apikey_id"))
        self.ct = get_object_or_404(ContentType, pk=kwargs.get("content_type_id"))
        self.object = get_object_or_404(self.ct.model_class(), pk=kwargs.get("obj_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["api_key"] = self.api_key
        context["current_title"] = _("Šalinti taikymo sritį")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            ): self.api_key,
            reverse("organization-apikeys", args=[self.organization.pk]): _("Raktai"),
        }
        return context

    def post(self, request, *args, **kwargs):
        if isinstance(self.object, Organization):
            scopes = ApiScope.objects.filter(key=self.api_key, organization=self.object)
        else:
            scopes = ApiScope.objects.filter(key=self.api_key, dataset=self.object)

        for sc in scopes:
            sc.delete()

        existing = ApiScope.objects.filter(key=self.api_key).values_list("scope", flat=True)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"scopes": list(existing)}
        error = False
        err_message = ""
        try:
            response = get_auth_session().patch(
                SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error updating scopes for apikey with client_id: {self.api_key.client_id}, {e}"
        else:
            if response.status_code != 200:
                error = True
                err_message = f"Error updating scopes for apikey with client_id: {self.api_key.client_id}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            )
        )

    def get_success_url(self):
        return reverse(
            "organization-apikeys-detail",
            kwargs={
                "pk": self.organization.pk,
                "apikey_id": self.kwargs.get("apikey_id"),
            },
        )


class OrganizationApiKeysScopeToggleView(PermissionRequiredMixin, View):
    def dispatch(self, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=self.kwargs.get("apikey_id"))
        return super().dispatch(*args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get(self, request, **kwargs):
        scope_name = kwargs.get("scope")
        if scope_name == "spinta_set_meta_fields" or scope_name == "set_meta_fields":
            scopes = ApiScope.objects.filter(key_id=self.api_key, scope__contains="set_meta_fields")
            for scope in scopes:
                if scope.enabled:
                    scope.enabled = False
                else:
                    scope.enabled = True
                scope.save()
        elif scope_name == "(viskas)":
            scopes = ApiScope.objects.filter(
                Q(key_id=self.api_key)
                & (
                    Q(scope="spinta_getone")
                    | Q(scope="spinta_getall")
                    | Q(scope="spinta_search")
                    | Q(scope="spinta_changes")
                )
            )
            for scope in scopes:
                if scope.enabled:
                    scope.enabled = False
                else:
                    scope.enabled = True
                scope.save()

        existing = ApiScope.objects.filter(key=self.api_key, enabled=True).values_list("scope", flat=True)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"scopes": list(existing)}
        error = False
        err_message = ""
        try:
            response = get_auth_session().patch(
                SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error toggling scopes for apikey with client_id {self.api_key.client_id}, {e}"
        else:
            if response.status_code != 200:
                error = True
                err_message = f"Error toggling scopes for apikey with client_id {self.api_key.client_id}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            )
        )


class OrganizationApiKeysToggleView(PermissionRequiredMixin, View):
    def dispatch(self, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=self.kwargs.get("apikey_id"))
        return super().dispatch(*args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.MANAGE_KEYS,
            self.organization,
        )

    def get(self, request, **kwargs):
        scopes = ApiScope.objects.filter(key=self.api_key)
        if self.api_key.enabled:
            self.api_key.enabled = False
        else:
            self.api_key.enabled = True
        self.api_key.save()
        if len(scopes) > 0:
            for scope in scopes:
                scope.enabled = self.api_key.enabled
                scope.save()
        return redirect(reverse("organization-apikeys", args=[self.organization.pk]))


class OrganizationApiKeysScopeObjectToggleView(PermissionRequiredMixin, View):
    def dispatch(self, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.api_key = get_object_or_404(ApiKey, pk=self.kwargs.get("apikey_id"))
        self.ct = get_object_or_404(ContentType, pk=kwargs.get("content_type_id"))
        self.object = get_object_or_404(self.ct.model_class(), pk=kwargs.get("obj_id"))
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

        existing = ApiScope.objects.filter(key=self.api_key, enabled=True).values_list("scope", flat=True)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"scopes": list(existing)}
        error = False
        err_message = ""
        try:
            response = get_auth_session().patch(
                SPINTA_SERVER_URL + "/auth/clients/" + self.api_key.client_id,
                json=data,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            error = True
            err_message = f"Error toggling scopes for apikey with client_id {self.api_key.client_id}, {e}"
        else:
            if response.status_code != 200:
                error = True
                err_message = f"Error toggling scopes for apikey with client_id {self.api_key.client_id}"
        if error:
            logger.warning(err_message)
            messages.error(self.request, _("Saugant API raktą įvyko klaida."))
        return redirect(
            reverse(
                "organization-apikeys-detail",
                args=[self.organization.pk, self.api_key.pk],
            )
        )


class OrganizationPlansHistoryView(PlanMixin, OrganizationBaseViewMixin, HistoryView):
    model = Organization
    detail_url_name = "organization-detail"
    history_url_name = "organization-plans-history"
    plan_url_name = "organization-plans"
    tabs_template_name = "vitrina/orgs/tabs.html"

    organization: Organization

    def get_history_objects(self):
        organization_plan_ids = Plan.objects.filter(receiver=self.organization).values_list("pk", flat=True)
        return (
            Version.objects.get_for_model(Plan)
            .filter(object_id__in=list(organization_plan_ids))
            .order_by("-revision__date_created")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_links"].update(
            {reverse("organization-plans", args=[self.organization.pk]): _("Planas"), None: _("Istorija")}
        )
        return context


class OrganizationMergeView(PermissionRequiredMixin, OrganizationBaseViewMixin, TemplateView):
    template_name = "base_form.html"

    organization: Organization

    def has_permission(self):
        return self.request.user and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Organizacijų sujungimas")
        context["parent_links"].update({None: _("Organizacijų sujungimas")})
        context["form"] = OrganizationMergeForm()
        return context

    def post(self, request, *args, **kwargs):
        form = OrganizationMergeForm(request.POST)
        if form.is_valid():
            merge_organization_id = form.cleaned_data.get("organization")
            return redirect(
                reverse(
                    "confirm-organization-merge",
                    args=[self.organization.pk, merge_organization_id],
                )
            )
        else:
            context = self.get_context_data(**kwargs)
            context["form"] = form
            return render(request, self.template_name, context)


class ConfirmOrganizationMergeView(PermissionRequiredMixin, TemplateView):
    template_name = "vitrina/orgs/confirm_merge.html"

    organization: Organization
    merge_organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("organization_id"))
        self.merge_organization = get_object_or_404(Organization, pk=kwargs.get("merge_organization_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.request.user and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Organizacijų sujungimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
        }
        context["organization"] = self.organization
        context["merge_organization"] = self.merge_organization

        # Related objects
        context["related_objects"] = {
            _("Duomenų ištekliai"): self.organization.dataset_set.all(),
            _("Ryšiai su duomenų ištekliais"): self.organization.datasetattribution_set.all(),
            _("Poreikiai ir pasiūlymai"): self.organization.request_set.all(),
            _("Tvarkytojai"): Representative.objects.filter(
                content_type=ContentType.objects.get_for_model(self.organization),
                object_id=self.organization.pk,
            ),
            _("Naudotojai"): self.organization.user_set.all(),
            _("Vaikinės organizacijos"): self.organization.get_children(),
            _("Užduotys"): self.organization.task_set.all(),
            _("Harvestinimo operacija"): self.organization.harvestingjob_set.all(),
            _("Finansavimo planai"): self.organization.financingplan_set.all(),
            _("Planai (organizacija paslaugų gavėjas)"): self.organization.receiver_plans.all(),
            _("Planai (organizacija paslaugų teikėjas)"): self.organization.publisher_plans.all(),
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
            object_id=self.merge_organization.pk,
        ).values_list("email", flat=True)
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
            obj.move(self.merge_organization, "sorted-child")

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

        for obj in self.organization.publisher_plans.all():
            obj.provider = self.merge_organization
            obj.save()

        self.organization.delete()

        request_assignments = RequestAssignment.objects.filter(organization=self.organization)
        for request_assignment in request_assignments:
            duplicate_ra = RequestAssignment.objects.filter(
                organization=self.merge_organization, request=request_assignment.request
            ).first()
            if duplicate_ra:
                duplicate_ra.delete()
            else:
                request_assignment.organization = self.merge_organization
                request_assignment.save()
        return redirect(reverse("organization-detail", args=[self.merge_organization.pk]))


class RepresentativeApiKeyView(PermissionRequiredMixin, TemplateView):
    template_name = "vitrina/orgs/api_key.html"

    organization: Organization
    representative: Representative

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get("pk"))
        self.representative = get_object_or_404(Representative, pk=kwargs.get("rep_id"))
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
        api_key = kwargs.get("key")
        data = serializer.loads(api_key)
        context["api_key"] = data.get("api_key")
        context["url"] = reverse("organization-members", args=[self.organization.pk])
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
            reverse("organization-members", args=[self.organization.pk]): _("Tvarkytojai"),
        }
        return context


class RepresentativeExistsView(TemplateView):
    template_name = "vitrina/orgs/partners/representative_exists.html"


class RepresentativeRequestExistsView(TemplateView):
    template_name = "vitrina/orgs/partners/representative_request_exists.html"


class AdminRemoteOrganizationSearchView(TemplateView):
    model_uri = "datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo"
    query_uri = "ja_pavadinimas.contains('{}')"
    company_code_query_uri = "ja_kodas={}"
    max_results = 20
    limit = 10

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "")
        if not q:
            return JsonResponse({"results": []})
        if q.isdigit():
            query = self.company_code_query_uri.format(q)
        else:
            query = self.query_uri.format(q) + f"&limit({self.limit})"

        data = get_data_from_spinta(model=self.model_uri, query=query)
        jar_data = data.get("_data", [])[: self.max_results]
        errors = data.get("errors", [])
        if errors:
            return JsonResponse({"results": [], "errors": errors})

        results = []
        for item in jar_data:
            company_name = item.get("ja_pavadinimas")
            company_code = item.get("ja_kodas")
            results.append(
                {
                    "id": company_code,
                    "text": company_name,
                    "company_code": company_code,
                }
            )

        return JsonResponse({"results": results})


def create_remote_organization(request):
    company_code = request.GET.get("company_code")
    publisher_id = request.GET.get("publisher_id")
    coordinator_id = request.GET.get("coordinator_id")
    exists = Organization.objects.filter(company_code=company_code).exists()
    model_uri = "datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo"
    query_uri = "ja_kodas={}"
    org = None

    if not exists:
        data = get_data_from_spinta(model=model_uri, query=query_uri.format(company_code))
        organization_data = data.get("_data", [])

        errors = data.get("errors", [])
        if errors:
            return JsonResponse({"errors": errors})

        if organization_data:
            org = Organization.add_root(
                title=organization_data[0].get("ja_pavadinimas"),
                company_code=organization_data[0].get("ja_kodas"),
                address=organization_data[0].get("pilnas_adresas"),
                is_public=True,
                publisher=False,
            )
            org.save()
    if exists:
        org = Organization.objects.get(company_code=company_code)

    if org:
        content_type = ContentType.objects.get_for_model(Organization)

        if publisher := Organization.objects.filter(pk=publisher_id):
            Representative.objects.get_or_create(
                content_type=content_type,
                object_id=org.id,
                organization=publisher.first(),
                role=Representative.OPEN_DATA_MANAGER,
            )
        if coordinator_id:
            coordinator = User.objects.filter(pk=coordinator_id).first()
            Representative.objects.get_or_create(
                content_type=content_type,
                object_id=org.id,
                user=coordinator,
                email=coordinator.email,
                role=Representative.OPEN_DATA_COORDINATOR,
            )

    return JsonResponse({"organization": org.pk if org else None})


def check_organization(request):
    company_code = request.GET.get("company_code")
    exists = Organization.objects.filter(company_code=company_code).exists()
    return JsonResponse({"exists": exists})
