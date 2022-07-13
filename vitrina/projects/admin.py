from django.contrib import admin

from vitrina.projects.models import Project


class ProjectAdmin(admin.ModelAdmin):
    list_filter = ('status',)


admin.site.register(Project, ProjectAdmin)
