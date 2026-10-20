from django.contrib import admin
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from vitrina.projects.models import Project, UseCaseClient, UseCaseClientScope
from vitrina.admin import RevisionCommentVersionAdmin


class ProjectAdmin(RevisionCommentVersionAdmin):
    list_display = ("__str__", "status", "is_public", "deleted")
    list_filter = ("status", "is_public", "deleted")
    search_fields = ("title",)
    readonly_fields = ("organization", "uuid")
    autocomplete_fields = ("datasets",)
    actions = ("restore_projects",)

    @admin.action(description=_("Atkurti ištrintus panaudojimo atvejus"))
    def restore_projects(self, request: WSGIRequest, queryset: QuerySet) -> None:
        for project in queryset.filter(deleted=True):
            project.deleted = None
            project.deleted_on = None
            project.save()

    def get_queryset(self, request: WSGIRequest) -> QuerySet:
        return super().get_queryset(request).select_related("user", "organization")


@admin.register(UseCaseClient)
class UseCaseClientAdmin(RevisionCommentVersionAdmin):
    list_display = ["use_case", "name", "client_id"]
    autocomplete_fields = ["use_case"]
    search_fields = ["use_case__title"]
    readonly_fields = ["client_id"]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("use_case")


@admin.register(UseCaseClientScope)
class UseCaseClientScopeAdmin(RevisionCommentVersionAdmin):
    list_display = ["resource", "action", "scope", "use_case_client"]
    autocomplete_fields = ["use_case_client"]
    search_fields = ["use_case_client__name"]

    def get_queryset(self, request) -> QuerySet:
        return super().get_queryset(request).select_related("use_case_client")


admin.site.register(Project, ProjectAdmin)
