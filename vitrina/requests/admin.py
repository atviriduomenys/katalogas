from django.contrib import admin

from vitrina.requests.models import Request, RequestAssignment
from reversion.admin import VersionAdmin


class RequestAdmin(VersionAdmin):
    list_filter = ('organizations',)

class RequestAssignmentAdmin(VersionAdmin):
    list_filter = ('organization',)

admin.site.register(Request, RequestAdmin)
admin.site.register(RequestAssignment, RequestAssignmentAdmin)
