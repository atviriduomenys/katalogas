from django.contrib import admin

from vitrina.structure.models import Prefix


class PrefixAdmin(admin.ModelAdmin):
    list_display = ('name', 'uri', 'object')


admin.site.register(Prefix, PrefixAdmin)
