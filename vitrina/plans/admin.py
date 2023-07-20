from django.contrib import admin
from reversion.admin import VersionAdmin

from vitrina.plans.forms import PlanAdminForm
from vitrina.plans.models import Project, Plan


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title',)


class PlanAdmin(VersionAdmin):
    list_display = ('title',)
    form = PlanAdminForm


admin.site.register(Project, ProjectAdmin)
admin.site.register(Plan, PlanAdmin)
