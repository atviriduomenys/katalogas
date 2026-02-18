import codecs
import logging
import uuid
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db import transaction
from django.forms import ModelForm, BaseForm
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from django_otp.plugins.otp_email.conf import settings
from requests.exceptions import ConnectionError as RequestsConnectionError

from vitrina.api.oauth import Secret, OAuthClientManagement
from vitrina.datasets.models import Dataset, Contact, Type, DCATResourceSubclass
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import (
    has_perm,
    Action,
)
from vitrina.structure.models import Metadata
from vitrina.uapi.models import RequestHistory
from vitrina.resources.models import Format
from vitrina.uapi.forms import AgentForm
from vitrina.uapi.models import Agent
from vitrina.views import PlanMixin

logger = logging.getLogger(__name__)


class BaseAgentView(LoginRequiredMixin, PermissionRequiredMixin, PlanMixin, TemplateView):
    organization_url_kwarg = "organization_id"
    template_name = "base_form.html"
    plan_url_name = "organization-plans"

    def setup(self, request, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.organization = get_object_or_404(Organization, pk=kwargs.get(self.organization_url_kwarg))

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "organization": self.organization,
                "organization_id": self.organization.pk,
                "can_view_members": has_perm(self.request.user, Action.VIEW, Representative, self.organization),
                "can_view_contacts": has_perm(self.request.user, Action.VIEW, Contact, self.organization),
                "can_update_organization": has_perm(
                    self.request.user, Action.UPDATE, Representative, self.organization
                ),
                "can_manage_keys": has_perm(self.request.user, Action.MANAGE_KEYS, self.organization),
                "can_view_agents": has_perm(self.request.user, Action.VIEW, Agent, self.organization),
                "can_view_keys": has_perm(self.request.user, Action.MANAGE_KEYS, Organization, self.organization),
            }
        )

        return context

    def get_plan_object(self) -> Organization:
        return self.organization


class AgentListView(BaseAgentView):
    template_name = "agents/agent_list.html"

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        organization_agents = (
            Agent.objects.filter(organization=self.organization, is_archived=False).order_by("-created_at").all()
        )

        paginator = Paginator(organization_agents, 10)
        page_number = self.request.GET.get("page")
        page = paginator.get_page(page_number)

        context.update(
            {
                "agents": page.object_list,
                "page_obj": page,
                "paginator": paginator,
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("organization-list"): _("Organizacijos"),
                    reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
                    None: _("Agentai"),
                },
                "has_permission": has_perm(self.request.user, Action.CREATE, Agent, self.organization),
            }
        )

        return context


class AgentDetailView(BaseAgentView):
    template_name = "agents/agent_detail.html"
    model = Agent

    def setup(self, request, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.object = get_object_or_404(
            Agent.objects.select_related("service").prefetch_related(("requesthistory")),
            pk=kwargs.get("pk"),
            organization=self.organization,
            is_archived=False,
        )

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        request_history = self.object.requesthistory.all()
        paginator = Paginator(request_history, 10)
        page_number = self.request.GET.get("page")
        page = paginator.get_page(page_number)

        context.update(
            {
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("organization-list"): _("Organizacijos"),
                    reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
                    reverse("agent-list", args=[self.organization.pk]): _("Agentai"),
                    None: _("Agentas"),
                },
                "page_obj": page,
                "paginator": paginator,
                "information_system": "",  # TODO: This will be added once Agent is not related to org. Add to template.
                "information_subsystem": "",  # TODO: This will be added once Agent is not related to org. Add to template.
                "agent": self.object,
                "dataset": self.object.service,
                "secret": self.request.session.pop("secret", None),
                "scopes": self.request.session.pop("scopes", None) or settings.OAUTH_AGENT_DEFAULT_SCOPES,
                "auth_server_host": settings.OAUTH_SERVER_HOST,
                "resource_server_host": f"{self.request.scheme}://{self.request.get_host()}",
                "request_history": page.object_list,
            }
        )

        return context


class AgentCreateView(CreateView, BaseAgentView):
    model = Agent
    form_class = AgentForm
    title = _("Pridėti Agentą")

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.object = None

    def get_form(self, form_class: AgentForm | None = None) -> ModelForm:
        form = super().get_form(form_class)
        form.fields["service"].help_text = _(
            "Nurodoma su Agentu susieta duomenų paslauga. Atitinka DCAT:DataService. Jei nenurodyta, duomenų paslauga bus sukurta automatiškai."
        )
        form.fields["service"].required = False
        return form

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE, Agent, self.organization)

    def form_valid(self, form: ModelForm) -> HttpResponse:
        title = form.cleaned_data["title"]
        service = form.cleaned_data.get("service")
        form.instance.organization = self.organization

        if not service:
            service = Dataset.add_root(
                title=f'Agento "{title}" Duomenų Paslauga',
                description="Ši duomenų paslauga buvo automatiškai sukurta kuriant Agentą.",
                access_rights=Dataset.NON_PUBLIC,
                organization=self.organization,
                service=True,
                subclass=DCATResourceSubclass.objects.get(name=DCATResourceSubclass.SERVICE),
                endpoint_url=None,
                endpoint_type=Format.objects.filter(extension="UAPI").first(),
                endpoint_description="https://ivpk.github.io/uapi",
                endpoint_description_type=Format.objects.filter(extension="Open API").first(),
                is_public=False,
            )
            form.instance.service = service
            form.instance.service.type.set(Type.objects.filter(name=Type.SERVICE).values_list("pk", flat=True))
            form.instance.service.save_translations()
            self.object = form.save()

            Metadata.objects.create(
                uuid=str(uuid.uuid4()),
                dataset=service,
                content_type=ContentType.objects.get_for_model(Dataset),
                object_id=service.pk,
                name=self.object.codename,
                title=title,
                description=_("Duomenų paslauga automatiškai sukurta kuriant agentą."),
                prepare_ast={},
                version=1,
            )

        if not hasattr(self, "object") or self.object is None:
            self.object = form.save()

        messages.success(self.request, _(f"Agentas {self.object.title} sukurtas sėkmingai!"))

        return redirect(reverse("agent-detail", args=[self.organization.pk, self.object.pk]))

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_title": self.title,
                "tabs": "vitrina/orgs/tabs.html",
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("organization-list"): _("Organizacijos"),
                    reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
                    reverse("agent-list", args=[self.organization.pk]): _("Agentai"),
                    None: self.title,
                },
            }
        )
        return context


class AgentUpdateView(UpdateView, BaseAgentView):
    model = Agent
    form_class = AgentForm
    title = _("Redaguoti Agentą")

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.object = get_object_or_404(Agent, pk=kwargs["pk"], organization=self.organization, is_archived=False)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_title": self.title,
                "tabs": "vitrina/orgs/tabs.html",
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("organization-list"): _("Organizacijos"),
                    reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
                    reverse("agent-list", args=[self.organization.pk]): _("Agentai"),
                    None: self.title,
                },
            }
        )
        return context

    def form_valid(self, form: ModelForm) -> HttpResponse:
        self.object = form.save()
        messages.success(self.request, _(f"Agentas {self.object.title} atnaujintas sėkmingai!"))
        return redirect(reverse("agent-list", args=[self.organization.pk]))


class AgentDeleteView(DeleteView, BaseAgentView):
    model = Agent
    template_name = "confirm_delete.html"

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.object = get_object_or_404(Agent, pk=kwargs["pk"], organization=self.organization, is_archived=False)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.DELETE, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("organization-list"): _("Organizacijos"),
                    reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
                    reverse("agent-list", args=[self.organization.pk]): _("Agentai"),
                    None: _("Pašalinti Agentą"),
                },
                "delete_text": _(f"Ar tikrai norite ištrinti Agentą: {self.object}?"),
            }
        )
        return context

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs.pop("organization")

        return kwargs

    def form_valid(self, form: BaseForm) -> HttpResponse:
        """Object is soft-deleted (archived) so to not lose the related service and other related objects."""
        self.object.is_archived = True
        self.object.save(update_fields=["is_archived", "updated_at"])
        messages.success(self.request, _(f"Agentas {self.object.title} pašalintas sėkmingai!"))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse("agent-list", kwargs={"organization_id": self.organization.id})


class RequestDetailView(BaseAgentView):
    template_name = "requests/request_detail.html"
    model = RequestHistory

    def setup(self, request, *args, **kwargs) -> None:
        self.object = get_object_or_404(
            RequestHistory.objects.select_related("agent__organization"),
            pk=kwargs.get("pk"),
        )
        kwargs[self.organization_url_kwarg] = self.object.agent.organization_id
        super().setup(request, *args, **kwargs)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        if isinstance(self.object.error, str):
            try:
                context["formatted_error"] = codecs.decode(self.object.error, "unicode_escape")
            except (UnicodeDecodeError, ValueError):
                context["formatted_error"] = self.object.error
        else:
            context["formatted_error"] = self.object.error

        context.update(
            {
                "request_history": self.object,
                "formatted_error": context["formatted_error"],
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("organization-list"): _("Organizacijos"),
                    reverse("organization-detail", args=[self.organization.pk]): self.organization.title,
                    reverse("agent-list", args=[self.organization.pk]): _("Agentai"),
                    reverse(
                        "agent-detail",
                        args=[self.organization.pk, self.object.agent.pk],
                    ): self.object.agent.title,
                    None: _("Užklausa"),
                },
            }
        )
        return context
