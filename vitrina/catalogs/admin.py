from django.contrib import admin
from .models import Catalog
from vitrina.admin import RevisionCommentVersionAdmin


@admin.register(Catalog)
class CatalogAdmin(RevisionCommentVersionAdmin):
    list_display = ("title", "identifier", "slug", "created", "modified")
    list_filter = ("created", "modified", "deleted", "licence")
    search_fields = ("title", "title_en", "identifier", "slug", "description")
    readonly_fields = ("created", "modified", "version")

    fieldsets = (
        ("Basic Information", {"fields": ("title", "title_en", "identifier", "slug")}),
        ("Content", {"fields": ("description", "licence")}),
        ("System Fields", {"fields": ("version", "created", "modified"), "classes": ("collapse",)}),
        ("Deletion", {"fields": ("deleted", "deleted_on"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1
        super().save_model(request, obj, form, change)
