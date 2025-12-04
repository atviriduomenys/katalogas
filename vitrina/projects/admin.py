from django.contrib import admin
from django.db.models import QuerySet
from reversion.admin import VersionAdmin
from vitrina.projects.models import Project, UseCaseClient, UseCaseClientScope
from vitrina.admin import JsonVersionAdmin


class ProjectAdmin(JsonVersionAdmin):
    list_filter = ("status",)
    search_fields = ("title",)
    readonly_fields = ("organization",)


@admin.register(UseCaseClient)
class UseCaseClientAdmin(VersionAdmin):
    list_display = ["use_case", "name", "client_id"]
    autocomplete_fields = ["use_case"]
    search_fields = ["use_case__title"]
    readonly_fields = ["client_id"]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("use_case")


@admin.register(UseCaseClientScope)
class UseCaseClientScopeAdmin(VersionAdmin):
    list_display = ["resource", "action", "scope", "use_case_client"]
    autocomplete_fields = ["use_case_client"]
    search_fields = ["use_case_client__name"]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("use_case_client")


admin.site.register(Project, ProjectAdmin)
