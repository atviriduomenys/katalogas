from django.contrib import admin

from vitrina.plans.forms import PlanAdminForm
from vitrina.plans.models import Project, Plan
from vitrina.admin import RevisionCommentVersionAdmin


class ProjectAdmin(RevisionCommentVersionAdmin):
    list_display = ("title",)


class PlanAdmin(RevisionCommentVersionAdmin):
    list_display = ("title",)
    form = PlanAdminForm


admin.site.register(Project, ProjectAdmin)
admin.site.register(Plan, PlanAdmin)
