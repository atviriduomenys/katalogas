from typing import Any, Optional

from django.contrib.admin import ModelAdmin
from django.contrib.admin.models import LogEntry
from django.http import HttpRequest
from reversion import revisions as reversion
from reversion.admin import VersionAdmin

from vitrina.utils import RevisionComment, RevisionSource


class JsonVersionAdmin(VersionAdmin):
    def _set_revision_comment(self, request: HttpRequest, obj: Any, action: str) -> None:
        if not reversion.is_active():
            return
        
        comment = RevisionComment(
            source=RevisionSource.ADMIN,
            action=action,
            http_method=request.method,
            path=request.path,
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