from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from django.db import transaction

from vitrina.structure.models import Prefix, ManifestValidationEntry
from vitrina.structure.tasks import validate_manifest_task
from vitrina.admin import RevisionCommentVersionAdmin


class PrefixAdmin(RevisionCommentVersionAdmin):
    list_display = ("name", "uri", "object")


class ManifestValidationEntryAdmin(RevisionCommentVersionAdmin):
    list_display = ("uuid", "created_at", "updated_at", "validation_status", "error_message")
    readonly_fields = ("created_at", "updated_at", "validation_status", "error_message")

    def save_model(self, request: HttpRequest, obj: ManifestValidationEntry, form: ModelForm, change: bool) -> None:
        super().save_model(request, obj, form, change)
        transaction.on_commit(lambda: validate_manifest_task.delay(obj.uuid, user_id=request.user.id))


admin.site.register(Prefix, PrefixAdmin)
admin.site.register(ManifestValidationEntry, ManifestValidationEntryAdmin)
