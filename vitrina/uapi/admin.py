from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from vitrina.uapi.models import Agent, RequestHistory, RequestHistoryChanges
from vitrina.admin import RevisionCommentVersionAdmin


@admin.register(Agent)
class AgentAdmin(RevisionCommentVersionAdmin):
    class Meta:
        verbose_name = _("Agentas")
        verbose_name_plural = _("Agentai")

    list_display = ["agent_name", "organization"]
    autocomplete_fields = ["service", "organization"]
    search_fields = ["codename", "service", "organization"]
    readonly_fields = ["codename"]

    @staticmethod
    def agent_name(obj: Agent) -> str:
        return str(obj)


@admin.register(RequestHistory)
class RequestHistoryAdmin(RevisionCommentVersionAdmin):
    autocomplete_fields = ["agent"]
    list_filter = ["agent"]


@admin.register(RequestHistoryChanges)
class RequestHistoryChangesAdmin(RevisionCommentVersionAdmin):
    pass
