import json
from typing import Any, Dict

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.http import HttpRequest
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html, escape
import reversion
from reversion.models import Revision, Version
from reversion.admin import VersionAdmin

from vitrina.utils import RevisionComment, RevisionSource


class VersionInline(admin.TabularInline):
    model = Version
    extra = 0
    can_delete = False

    fields = (
        "version_data",
        "column_content_type",
        "column_object_id",
        "column_object_repr",
    )
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest, obj: Revision | None = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Revision | None = None) -> bool:
        return False

    @admin.display(description="Versijos duomenys")
    def version_data(self, obj: Version) -> str:
        data = obj.field_dict
        data_json = json.dumps(data, indent=2, ensure_ascii=False, default=str)

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
            escape(data_json),
        )

    @admin.display(description="Modelis")
    def column_content_type(self, obj: Version) -> Any:
        return obj.content_type

    @admin.display(description="Objekto ID")
    def column_object_id(self, obj: Version) -> str:
        try:
            url = reverse(
                f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                args=[obj.object_id],
            )
        except NoReverseMatch:
            return str(obj.object_id)

        return format_html('<a href="{}">{}</a>', url, obj.object_id)

    @admin.display(description="Objektas")
    def column_object_repr(self, obj: Version) -> str:
        return obj.object_repr


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ("id", "date_created", "user", "comment")
    date_hierarchy = "date_created"
    search_fields = ("user__username", "comment")
    inlines = [VersionInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Revision | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Revision | None = None) -> bool:
        return False

    def get_actions(self, request: HttpRequest) -> Dict[str, Any]:
        return {}


class RevisionCommentVersionAdmin(VersionAdmin):
    def _set_revision_comment(self, request: HttpRequest, obj: Any, action: str) -> None:
        if not reversion.is_active():
            return

        view_args = list(request.resolver_match.args)
        view_kwargs = dict(request.resolver_match.kwargs)

        comment = RevisionComment(
            source=RevisionSource.ADMIN,
            action=action,
            http_method=request.method,
            path=request.path,
            args=view_args,
            kwargs=view_kwargs,
        )
        reversion.set_comment(comment.to_json())

    def log_addition(self, request: HttpRequest, obj: Any, message: str) -> LogEntry:
        log_entry = super().log_addition(request, obj, message)
        self._set_revision_comment(request, obj, "add")
        return log_entry

    def log_change(self, request: HttpRequest, obj: Any, message: str) -> LogEntry:
        log_entry = super().log_change(request, obj, message)
        self._set_revision_comment(request, obj, "change")
        return log_entry

    def log_deletion(self, request: HttpRequest, obj: Any, object_repr: str) -> LogEntry:
        log_entry = super().log_deletion(request, obj, object_repr)
        self._set_revision_comment(request, obj, "delete")
        return log_entry
