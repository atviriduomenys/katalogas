from django.contrib import admin
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from vitrina.smart_contracts.models import (
    Agreement,
    AgreementScope,
    SmartContractTemplate,
)


@admin.register(SmartContractTemplate)
class SmartContractTemplateAdmin(admin.ModelAdmin):
    class Meta:
        verbose_name = _("Išmaniųjų sutarčių numatytasis šablonas")
        verbose_name_plural = _("Išmaniųjų sutarčių numatytieji šablonai")


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    class Meta:
        verbose_name = _("Sutartis")
        verbose_name_plural = _("Sutartys")

    list_display = [
        "project",
        "assigner_organization",
        "status",
        "is_agent_sync_enabled",
        "last_sync_date",
    ]
    autocomplete_fields = ["project", "assigner_organization"]
    search_fields = ["project__title", "organization__title"]
    readonly_fields = ["last_sync_date", "created_at", "updated_at"]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("project", "assigner_organization")


@admin.register(AgreementScope)
class AgreementScopeAdmin(admin.ModelAdmin):
    class Meta:
        verbose_name = _("Sutarties leidimas")
        verbose_name_plural = _("Sutarties leidimai")

    list_display = ["agreement", "resource"]
    autocomplete_fields = ["agreement"]
    search_fields = ["agreement__project__title", "agreement__assigner_organization__title"]

    def get_queryset(self, request) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("agreement__project", "agreement__assigner_organization")
        )
