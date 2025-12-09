from django.contrib import admin

from vitrina.viisp.models import ViispKey, ViispTokenKey
from vitrina.admin import RevisionCommentVersionAdmin


class ViispKeyAdmin(RevisionCommentVersionAdmin):
    list_display = ("key_content",)


class ViispTokenKeyAdmin(RevisionCommentVersionAdmin):
    list_display = ("key_content",)


admin.site.register(ViispKey, ViispKeyAdmin)
admin.site.register(ViispTokenKey, ViispTokenKeyAdmin)
