from django.contrib import admin

from vitrina.structure.models import Prefix, DsaValidationEntry
from vitrina.structure.tasks import validate_dsa_task


class PrefixAdmin(admin.ModelAdmin):
    list_display = ("name", "uri", "object")


class DsaValidationEntryAdmin(admin.ModelAdmin):
    list_display = ("uuid", "created_at", "updated_at", "validation_status", "error_message")
    readonly_fields = ("created_at", "updated_at", "validation_status", "error_message")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        validate_dsa_task.delay(obj.uuid)


admin.site.register(Prefix, PrefixAdmin)
admin.site.register(DsaValidationEntry, DsaValidationEntryAdmin)
