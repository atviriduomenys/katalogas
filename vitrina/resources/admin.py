from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from vitrina.resources.forms import FormatAdminForm
from vitrina.resources.models import Format, GeoportalFormat, GeoportalFormatValue, CompressionFormat, PackagingFormat


class FormatAdmin(admin.ModelAdmin):
    form = FormatAdminForm


class GeoportalFormatValueInline(admin.TabularInline):
    model = GeoportalFormatValue
    extra = 0


class GeoportalFormatAdmin(admin.ModelAdmin):
    inlines = [GeoportalFormatValueInline]
    list_display = (
        "format",
        "values_display",
    )

    def values_display(self, obj):
        return mark_safe(
            "<br/>".join([item.value for item in obj.geoportalformatvalue_set.all()])
        )

    values_display.short_description = _("Geoportalo reikšmės")


class CompressionFormatAdmin(admin.ModelAdmin):
    fields = (
        "title",
        "extension",
        "uri"
    )


class PackagingFormatAdmin(admin.ModelAdmin):
    fields = (
        "title",
        "extension",
        "uri"
    )


admin.site.register(Format, FormatAdmin)
admin.site.register(GeoportalFormat, GeoportalFormatAdmin)
admin.site.register(CompressionFormat, CompressionFormatAdmin)
admin.site.register(PackagingFormat, PackagingFormatAdmin)
