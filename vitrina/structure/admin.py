from django.contrib import admin

from vitrina.structure.models import Prefix, ManifestType


class PrefixAdmin(admin.ModelAdmin):
    list_display = ('name', 'uri', 'object')


class ManifestTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'title',)


admin.site.register(Prefix, PrefixAdmin)
admin.site.register(ManifestType, ManifestTypeAdmin)
