from django.contrib import admin

from vitrina.requests.models import Request, RequestAssignment, RequestEscalation
from vitrina.admin import RevisionCommentVersionAdmin


class RequestAdmin(RevisionCommentVersionAdmin):
    list_filter = ("organizations",)


class RequestAssignmentAdmin(RevisionCommentVersionAdmin):
    list_filter = ("organization",)


class RequestEscalationAdmin(RevisionCommentVersionAdmin):
    list_filter = ("request",)


admin.site.register(Request, RequestAdmin)
admin.site.register(RequestAssignment, RequestAssignmentAdmin)
admin.site.register(RequestEscalation, RequestEscalationAdmin)
