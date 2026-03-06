import codecs
import logging
from typing import Any
from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.paginator import Paginator
from django.forms import ModelForm, BaseForm
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    ListView,
    DetailView,
)

from django_otp.plugins.otp_email.conf import settings
from requests.exceptions import ConnectionError as RequestsConnectionError
from vitrina.api.oauth import OAuthClientManagement
from vitrina.orgs.services import (
    has_perm,
    Action,
)
from vitrina.uapi.models import RequestHistory, Agent, AgentEnvironment
from vitrina.uapi.forms import AgentForm, AgentEnvironmentForm
from vitrina.views import PlanMixin
from vitrina.orgs.views import OrganizationBaseViewMixin

logger = logging.getLogger(__name__)


class BaseAgentMixin(OrganizationBaseViewMixin):
    organization_url_kwarg = "organization_id"
    agent: Agent

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["parent_links"].update(
            {
                reverse("agent-list", args=[self.organization.pk]): _("Agentai"),
                reverse("agent-detail", args=[self.organization.pk, self.agent.pk]): self.agent.title,
            }
        )
        return context

    @property
    def agent(self) -> Agent:
        return self.object


class BaseAgentEnvMixin(BaseAgentMixin):
    agent_environment: AgentEnvironment

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["parent_links"].update(
            {
                reverse(
                    "agent-env-detail", args=[self.organization.pk, self.agent_environment.pk]
                ): self.agent_environment.get_environment_display()
            }
        )
        return context

    @property
    def agent(self) -> Agent:
        return self.agent_environment.agent

    @property
    def agent_environment(self) -> Agent:
        return self.object


class AgentListView(LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, ListView):
    model = Agent
    template_name = "agents/agent_list.html"
    context_object_name = "agents"
    paginate_by = 10

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, Agent, self.organization)

    def get_queryset(self):
        return self.model.not_archived.filter(organization=self.organization).order_by("-created_at")

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Agentai")
        context["can_create_agents"] = has_perm(self.request.user, Action.CREATE, Agent, self.organization)
        context["parent_links"].update({None: _("Agentai")})

        return context


class AgentDetailView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentMixin, PlanMixin, DetailView):
    template_name = "agents/agent_detail.html"
    model = Agent

    def get_queryset(self):
        return self.model.not_archived.filter(organization=self.organization).prefetch_related("environments")

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": {"title": self.object.title, "object_type": _("Agentas")},
                "information_system": "",  # TODO: This will be added once Agent is not related to org. Add to template.
                "information_subsystem": "",  # TODO: This will be added once Agent is not related to org. Add to template.
                "can_create_agent_env": has_perm(self.request.user, Action.CREATE, AgentEnvironment, self.organization),
                "environments": self.object.environments.filter(is_archived=False),
            }
        )
        context["parent_links"].update(
            {None: context["parent_links"].pop(reverse("agent-detail", args=[self.organization.pk, self.object.pk]))}
        )

        return context


class AgentCreateView(LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, CreateView):
    model = Agent
    form_class = AgentForm
    title = _("Pridėti Agentą")
    template_name = "base_form.html"

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE, Agent, self.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        return kwargs

    def form_valid(self, form: ModelForm) -> HttpResponse:
        form.instance.organization = self.organization
        response = super().form_valid(form)
        messages.success(self.request, _("Agentas '{0}' sukurtas sėkmingai!").format(self.object.title))

        return response

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = self.title
        context["parent_links"].update(
            {
                reverse("agent-list", args=[self.organization.pk]): _("Agentai"),
                None: _("Pridėti"),
            }
        )
        return context

    def get_success_url(self):
        return reverse("agent-detail", args=[self.organization.pk, self.object.pk])


class AgentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentMixin, PlanMixin, UpdateView):
    model = Agent
    form_class = AgentForm
    title = _("Redaguoti Agentą")
    template_name = "base_form.html"

    def get_queryset(self):
        return self.model.not_archived.filter(organization=self.organization)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = self.title
        context["parent_links"].update(
            {
                None: _("Redaguoti"),
            }
        )
        return context

    def form_valid(self, form: ModelForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("Agentas '{0}' atnaujintas sėkmingai!").format(self.object.title))
        return response

    def get_success_url(self):
        return reverse("agent-list", args=[self.organization.pk])


class AgentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentMixin, PlanMixin, DeleteView):
    model = Agent
    template_name = "confirm_delete.html"

    def get_queryset(self):
        return self.model.not_archived.filter(organization=self.organization)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.DELETE, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["parent_links"].update(
            {
                None: _("Pašalinti"),
            }
        )
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        """Object is soft-deleted (archived) so to not lose the related service and other related objects."""
        self.object.is_archived = True
        self.object.save(update_fields=["is_archived", "updated_at"])
        messages.success(self.request, _("Agentas '{0}' pašalintas sėkmingai!").format(self.object.title))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse("agent-list", args=[self.organization.id])


class AgentEnvDetailView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentEnvMixin, PlanMixin, DetailView):
    model = AgentEnvironment
    template_name = "agents/agent_env_detail.html"
    context_object_name = "agent_environment"

    def get_queryset(self):
        return self.model.not_archived.filter(agent__organization=self.organization).prefetch_related("requesthistory")

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, AgentEnvironment, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        request_history = self.object.requesthistory.all().order_by("-created_at")
        paginator = Paginator(request_history, 10)
        page_number = self.request.GET.get("page")
        page = paginator.get_page(page_number)

        context.update(
            {
                "page_title": {"title": self.object, "object_type": _("Aplinka")},
                "page_obj": page,
                "information_system": "",  # TODO: This will be added once Agent is not related to org. Add to template.
                "information_subsystem": "",  # TODO: This will be added once Agent is not related to org. Add to template.
                "secret": self.request.session.pop("secret", None),
                "scopes": self.request.session.pop("scopes", None) or settings.OAUTH_AGENT_DEFAULT_SCOPES,
                "auth_server_host": settings.OAUTH_SERVER_HOST,
                "resource_server_host": f"{self.request.scheme}://{self.request.get_host()}",
                "request_history": page.object_list,
            }
        )
        context["parent_links"].update(
            {
                None: context["parent_links"].pop(
                    reverse("agent-env-detail", args=[self.organization.pk, self.object.pk])
                )
            }
        )

        return context


class AgentEnvCreateView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentMixin, PlanMixin, CreateView):
    model = AgentEnvironment
    form_class = AgentEnvironmentForm
    template_name = "base_form.html"
    title = _("Pridėti aplinką")

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE, AgentEnvironment, self.organization)

    def form_valid(self, form: ModelForm) -> HttpResponse:
        form.instance.agent = self.agent
        self.object: AgentEnvironment = form.save(commit=False)
        try:
            client_id, secret = OAuthClientManagement.create_oauth_client(scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)
            self.object.oauth_client_id = client_id
            self.object.save()
            self.request.session["secret"] = secret
            self.request.session["scopes"] = settings.OAUTH_AGENT_DEFAULT_SCOPES

            messages.success(
                self.request,
                _("Aplinka '{0}' sukurta sėkmingai!").format(self.object),
            )
            messages.warning(
                self.request,
                _(
                    "Išsisaugokite slaptą raktą rodomą puslapio pabaigoje, jis bus rodomas tik šį kartą!\n "
                    'Jei pasirinkote rūšį "Spinta", raktas vaizduojamas šalia stulpelio "secret" credentials.cfg '
                    "failo pavyzdyje"
                ),
            )
        except RequestsConnectionError:
            error = _("Nepavyko pasiekti autorizacijos serverio (%(url)s), dėl to Agento aplinkos kūrimas nepavyko.")
            messages.error(self.request, error % {"url": settings.OAUTH_SERVER_CLIENTS_URL})
            return self.form_invalid(form)

        except Exception as general_exception:
            error = _("Įvyko klaida, nepavyko sukurti Agento aplinkos. Klaida: %(exception)s")
            messages.error(self.request, error % {"exception": str(general_exception)})
            return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = self.title
        context["parent_links"].update({None: self.title})
        return context

    def get_success_url(self):
        return reverse(
            "agent-env-detail",
            kwargs={"organization_id": self.organization.pk, "pk": self.object.pk},
        )

    @cached_property
    def agent(self) -> Agent:
        return get_object_or_404(Agent, organization=self.organization, pk=self.kwargs.get("pk"))


class AgentEnvUpdateView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentEnvMixin, PlanMixin, UpdateView):
    model = AgentEnvironment
    form_class = AgentEnvironmentForm
    template_name = "base_form.html"
    title = _("Redaguoti aplinką")

    def get_queryset(self):
        return self.model.not_archived.filter(agent__organization=self.organization)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE, AgentEnvironment, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = self.title

        context["parent_links"].update(
            {
                None: self.title,
            }
        )
        return context

    def form_valid(self, form: ModelForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("'{0}' aplinka atnaujinta sėkmingai!").format(self.object))
        return response

    def get_success_url(self) -> str:
        return reverse("agent-detail", args=[self.organization.pk, self.object.agent.pk])


class AgentEnvDeleteView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentEnvMixin, PlanMixin, DeleteView):
    model = AgentEnvironment
    template_name = "confirm_delete.html"

    def get_queryset(self):
        return self.model.not_archived.filter(agent__organization=self.organization)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.DELETE, AgentEnvironment, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["delete_text"] = _("Ar tikrai norite ištrinti aplinką: {0}?").format(self.object)
        context["parent_links"].update(
            {
                None: _("Pašalinti"),
            }
        )
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        """Object is soft-deleted (archived) so to not lose the related service and other related objects."""
        self.object.is_archived = True
        self.object.save(update_fields=["is_archived", "updated_at"])
        messages.success(self.request, _("'{0}' aplinka pašalinta sėkmingai!").format(self.object))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse("agent-detail", kwargs={"organization_id": self.organization.id, "pk": self.agent.pk})


class RequestDetailView(LoginRequiredMixin, PermissionRequiredMixin, BaseAgentEnvMixin, PlanMixin, DetailView):
    template_name = "requests/request_detail.html"
    model = RequestHistory

    def get_queryset(self):
        return self.model.visible.filter(agent_environment__agent__organization=self.organization)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, Agent, self.organization)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context["page_title"] = {"title": _("Užklausa"), "object_type": _("Užklausa")}

        if isinstance(self.object.error, str):
            try:
                context["formatted_error"] = codecs.decode(self.object.error, "unicode_escape")
            except (UnicodeDecodeError, ValueError):
                context["formatted_error"] = self.object.error
        else:
            context["formatted_error"] = self.object.error

        context.update({"request_history": self.object, "formatted_error": context["formatted_error"]})
        context["parent_links"].update({None: _("Užklausa")})
        return context

    @property
    def agent_environment(self) -> AgentEnvironment:
        return self.object.agent_environment
