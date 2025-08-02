from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from reversion.admin import VersionAdmin

from vitrina.uapi.models import Agent, RequestHistory, RequestHistoryChanges


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    class Meta:
        verbose_name = _("Agentas")
        verbose_name_plural = _("Agentai")

    list_display = ["agent_name", "organization"]
    autocomplete_fields = ["service", "organization"]
    search_fields = ["codename", "service", "organization"]
    readonly_fields = ["codename", "synchronized_at", "is_last_sync_successful"]

    @staticmethod
    def agent_name(obj: Agent) -> str:
        return str(obj)


@admin.register(RequestHistory)
class RequestHistoryAdmin(VersionAdmin):
    list_filter = ("agent",)


@admin.register(RequestHistoryChanges)
class RequestHistoryChangesAdmin(admin.ModelAdmin):
    pass
