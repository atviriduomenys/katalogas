from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from vitrina.uapi.models import Agent, RequestHistory, RequestHistoryChanges, AgentEnv
from vitrina.admin import RevisionCommentVersionAdmin


class AgentEnvInline(admin.TabularInline):
    model = AgentEnv
    extra = 1
    readonly_fields = ["synchronized_at", "is_last_sync_successful", "oauth_client_id"]


@admin.register(Agent)
class AgentAdmin(RevisionCommentVersionAdmin):
    class Meta:
        verbose_name = _("Agentas")
        verbose_name_plural = _("Agentai")

    list_display = ["agent_name", "organization"]
    autocomplete_fields = ["organization"]
    search_fields = ["codename", "organization"]
    readonly_fields = ["codename"]
    inlines = [AgentEnvInline]

    @staticmethod
    def agent_name(obj: Agent) -> str:
        return str(obj)



@admin.register(RequestHistory)
class RequestHistoryAdmin(RevisionCommentVersionAdmin):
    autocomplete_fields = ["agent_env"]
    list_filter = ["agent_env"]


@admin.register(RequestHistoryChanges)
class RequestHistoryChangesAdmin(RevisionCommentVersionAdmin):
    pass


@admin.register(AgentEnv)
class AgentEnvAdmin(RevisionCommentVersionAdmin):
    search_fields = [
        "agent__title",
        "agent__codename",
    ]
