from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from vitrina.resources.forms import FormatAdminForm
from vitrina.resources.models import (
    DatasetDistribution,
    Format,
    GeoportalFormat,
    GeoportalFormatValue,
    CompressionFormat,
    PackagingFormat,
    MediaType,
)
from vitrina.admin import RevisionCommentVersionAdmin


class FormatAdmin(RevisionCommentVersionAdmin):
    form = FormatAdminForm


class GeoportalFormatValueInline(admin.TabularInline):
    model = GeoportalFormatValue
    extra = 0


class GeoportalFormatAdmin(RevisionCommentVersionAdmin):
    inlines = [GeoportalFormatValueInline]
    list_display = (
        "format",
        "values_display",
    )

    def values_display(self, obj):
        return mark_safe("<br/>".join([item.value for item in obj.geoportalformatvalue_set.all()]))

    values_display.short_description = _("Geoportalo reikšmės")


class CompressionFormatAdmin(RevisionCommentVersionAdmin):
    fields = ("title", "extension", "uri")


class PackagingFormatAdmin(RevisionCommentVersionAdmin):
    fields = ("title", "extension", "uri")


class MediaTypeAdmin(RevisionCommentVersionAdmin):
    fields = ("title", "uri")


class DatasetDistributionAdmin(RevisionCommentVersionAdmin):
    list_display = ("__str__", "dataset", "format", "data_last_updated")
    list_filter = ("format",)
    search_fields = ("translations__title", "dataset__translations__title")
    readonly_fields = ("created", "modified")
    fieldsets = ((None, {"fields": ("dataset", "format", "data_last_updated", "created", "modified")}),)


admin.site.register(DatasetDistribution, DatasetDistributionAdmin)
admin.site.register(Format, FormatAdmin)
admin.site.register(GeoportalFormat, GeoportalFormatAdmin)
admin.site.register(CompressionFormat, CompressionFormatAdmin)
admin.site.register(PackagingFormat, PackagingFormatAdmin)
admin.site.register(MediaType, MediaTypeAdmin)
