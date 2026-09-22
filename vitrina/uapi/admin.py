from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from vitrina.uapi.models import Agent, RequestHistory, RequestHistoryChanges, AgentEnvironment
from vitrina.admin import RevisionCommentVersionAdmin


@admin.register(Agent)
class AgentAdmin(RevisionCommentVersionAdmin):
    class Meta:
        verbose_name = _("Agentas")
        verbose_name_plural = _("Agentai")

    list_display = ["agent_name", "organization"]
    autocomplete_fields = ["organization"]
    search_fields = ["codename", "organization__title"]
    readonly_fields = ["codename"]

    @staticmethod
    def agent_name(obj: Agent) -> str:
        return str(obj)

    def has_delete_permission(self, request: HttpRequest, obj: Agent | None = None) -> bool:
        # Deleting an agent cascades to its environments, see AgentEnvAdmin.has_delete_permission.
        return False


@admin.register(RequestHistory)
class RequestHistoryAdmin(RevisionCommentVersionAdmin):
    autocomplete_fields = ["agent_environment"]
    list_filter = ["agent_environment"]


@admin.register(AgentEnvironment)
class AgentEnvAdmin(RevisionCommentVersionAdmin):
    class Meta:
        verbose_name = _("Agento aplinka")
        verbose_name_plural = _("Agento aplinkos")

    search_fields = [
        "agent__title",
        "agent__organization__title",
        "environment",
        "instance_uri",
    ]
    list_display = ["environment", "agent"]
    readonly_fields = ["synchronized_at", "is_last_sync_successful", "instance_uri", "oauth_client_id"]
    autocomplete_fields = ["agent"]

    def has_delete_permission(self, request: HttpRequest, obj: AgentEnvironment | None = None) -> bool:
        # Environments are archived, never deleted: the app has deletion switched off too. Recovering a
        # deleted environment from a version saved before `instance_uri` existed would issue a new
        # identifier, and the `agent_id` a deployed agent holds would stop matching.
        return False


@admin.register(RequestHistoryChanges)
class RequestHistoryChangesAdmin(RevisionCommentVersionAdmin):
    pass
