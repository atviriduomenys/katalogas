import json
from typing import Any, Dict, Optional

from django.contrib import admin
from django.http import HttpRequest
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html, escape
from reversion.models import Revision, Version


class VersionInline(admin.TabularInline):
    model = Version
    extra = 0
    can_delete = False

    fields = (
        "version_data",
        "col_content_type",
        "col_object_id",
        "col_object_repr",
    )
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest, obj: Optional[Revision] = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Optional[Revision] = None) -> bool:
        return False

    @admin.display(description="Versijos duomenys")
    def version_data(self, obj: Version) -> str:
        data = obj.field_dict
        pretty = json.dumps(data, indent=2, ensure_ascii=False, default=str)

        element_id = f"snapshot-{obj.pk}"

        return format_html(
            (
                '<a href="#" onclick="'
                "var el=document.getElementById('{}');"
                "if(el.style.display==='none' || !el.style.display){{"
                "el.style.display='block';"
                "this.innerText='Slėpti &#9650;';"
                "}}else{{"
                "el.style.display='none';"
                "this.innerText='Rodyti &#9660;';"
                "}}"
                "return false;"
                '">Rodyti &#9660;</a>'
                '<div id="{}" style="display:none; margin-top:4px;">'
                "<pre style='white-space:pre-wrap; margin:0;'>{}</pre>"
                "</div>"
            ),
            element_id,
            element_id,
            escape(pretty),
        )

    @admin.display(description="Modelis")
    def col_content_type(self, obj: Version) -> Any:
        return obj.content_type

    @admin.display(description="Objekto ID")
    def col_object_id(self, obj: Version) -> str:
        try:
            url = reverse(
                f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                args=[obj.object_id],
            )
        except NoReverseMatch:
            return str(obj.object_id)

        return format_html('<a href="{}">{}</a>', url, obj.object_id)

    @admin.display(description="Objektas")
    def col_object_repr(self, obj: Version) -> str:
        return obj.object_repr


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ("id", "date_created", "user", "comment")
    date_hierarchy = "date_created"
    search_fields = ("user__username", "comment")
    inlines = [VersionInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Optional[Revision] = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Optional[Revision] = None) -> bool:
        return False

    def get_actions(self, request: HttpRequest) -> Dict[str, Any]:
        return {}
