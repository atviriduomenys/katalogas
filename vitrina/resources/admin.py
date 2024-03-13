from django.contrib import admin

from vitrina.resources.forms import FormatAdminForm
from vitrina.resources.models import Format


class FormatAdmin(admin.ModelAdmin):
    form = FormatAdminForm


admin.site.register(Format, FormatAdmin)

