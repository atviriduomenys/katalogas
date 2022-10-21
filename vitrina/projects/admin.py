from django.contrib import admin
from reversion.admin import VersionAdmin

from vitrina.projects.models import Project


class ProjectAdmin(VersionAdmin):
    list_filter = ('status',)


admin.site.register(Project, ProjectAdmin)
