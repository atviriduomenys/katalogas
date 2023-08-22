from django.contrib import admin

from vitrina.requests.models import Request
from reversion.admin import VersionAdmin


class RequestAdmin(VersionAdmin):
    list_filter = ('organizations',)


admin.site.register(Request, RequestAdmin)
