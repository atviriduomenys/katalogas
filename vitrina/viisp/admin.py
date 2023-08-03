from django.contrib import admin

from vitrina.viisp.models import ViispKey


class ViispAdmin(admin.ModelAdmin):
    list_display = ('key_content',)

admin.site.register(ViispKey, ViispAdmin)
