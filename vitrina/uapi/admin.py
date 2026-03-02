from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from vitrina.uapi.models import Agent, RequestHistory, RequestHistoryChanges, AgentEnv
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


@admin.register(RequestHistory)
class RequestHistoryAdmin(RevisionCommentVersionAdmin):
    autocomplete_fields = ["agent_env"]
    list_filter = ["agent_env"]


@admin.register(AgentEnv)
class AgentEnvAdmin(RevisionCommentVersionAdmin):
    class Meta:
        verbose_name = _("Agento aplinka")
        verbose_name_plural = _("Agento aplinkos")

    search_fields = [
        "agent__title",
        "agent__organization__title",
        "environment",
    ]
    list_display = ["environment", "agent"]
    readonly_fields = ["synchronized_at", "is_last_sync_successful", "oauth_client_id"]
    autocomplete_fields = ["agent"]


@admin.register(RequestHistoryChanges)
class RequestHistoryChangesAdmin(RevisionCommentVersionAdmin):
    pass
