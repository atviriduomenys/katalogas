from django.contrib import admin
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from vitrina.smart_contracts.models import (
    Agreement,
    AgreementScope,
    SmartContractTemplate,
    AgreementFile,
)
from vitrina.admin import RevisionCommentVersionAdmin


@admin.register(SmartContractTemplate)
class SmartContractTemplateAdmin(RevisionCommentVersionAdmin):
    class Meta:
        verbose_name = _("Išmaniųjų sutarčių numatytasis šablonas")
        verbose_name_plural = _("Išmaniųjų sutarčių numatytieji šablonai")


@admin.register(Agreement)
class AgreementAdmin(RevisionCommentVersionAdmin):
    list_display = [
        "project",
        "assigner",
        "status",
        "is_agent_sync_enabled",
        "last_sync_date",
    ]
    autocomplete_fields = ["project", "assigner"]
    search_fields = ["project__title", "organization__title"]
    readonly_fields = ["last_sync_date", "created_at", "updated_at"]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("project", "assigner")


@admin.register(AgreementScope)
class AgreementScopeAdmin(RevisionCommentVersionAdmin):
    list_display = ["agreement", "scope"]
    autocomplete_fields = ["agreement"]
    search_fields = [
        "agreement__project__title",
        "agreement__assigner__title",
    ]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("agreement__project", "agreement__assigner")


@admin.register(AgreementFile)
class AgreementFileAdmin(RevisionCommentVersionAdmin):
    list_display = ["agreement", "file_name", "file_extension"]
    autocomplete_fields = ["agreement"]
    search_fields = [
        "agreement__project__title",
        "agreement__assigner__title",
    ]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("agreement__project", "agreement__assigner")
