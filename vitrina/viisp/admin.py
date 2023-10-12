from django.contrib import admin

from vitrina.viisp.models import ViispKey, ViispTokenKey


class ViispKeyAdmin(admin.ModelAdmin):
    list_display = ('key_content',)

class ViispTokenKeyAdmin(admin.ModelAdmin):
    list_display = ('key_content',)

admin.site.register(ViispKey, ViispKeyAdmin)
admin.site.register(ViispTokenKey, ViispTokenKeyAdmin)

