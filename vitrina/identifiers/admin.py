from django.contrib import admin

from .models import Identifier, Agency


class IdentifierInline(admin.TabularInline):
    model = Identifier
    extra = 0
    fields = ("notation", "identifier_type", "scheme_agency", "resource")
    autocomplete_fields = ("scheme_agency", "resource")


@admin.register(Identifier)
class IdentifierAdmin(admin.ModelAdmin):
    list_display = (
        "notation",
        "identifier_type",
        "scheme_agency",
        "resource",
    )
    list_filter = (
        "identifier_type",
        "resource",
    )
    search_fields = (
        "notation",
        "scheme_agency__name",
        "resource__description",
    )
    ordering = ("notation",)
    autocomplete_fields = ("scheme_agency", "resource")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "resource",
                    "notation",
                    "identifier_type",
                    "scheme_agency",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("scheme_agency")


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "uri")
    search_fields = ("name", "uri")
    inlines = [IdentifierInline]
