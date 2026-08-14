from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from djangocms_stories.admin import PostAdmin as OriginalPostAdmin
from djangocms_stories.models import Post

from vitrina.cms.forms import (
    LearningMaterialAdminForm,
    FaqAdminForm,
    ExternalSiteAdminForm,
    PublishedReportAdminForm,
    DeploymentAdminForm,
)
from vitrina.cms.models import (
    LearningMaterial,
    Faq,
    ExternalSite,
    Deployment,
    LearningMaterialFile,
)
from vitrina.orgs.models import PublishedReport
from vitrina.admin import RevisionCommentVersionAdmin


class LearningMaterialFileInline(admin.TabularInline):
    model = LearningMaterialFile
    extra = 1
    fields = ("file", "name")


class LearningMaterialAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "topic",
        "published",
    )
    form = LearningMaterialAdminForm
    inlines = [LearningMaterialFileInline]

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1
        if not obj.user:
            obj.user = request.user

        super().save_model(request, obj, form, change)


class FaqAdmin(RevisionCommentVersionAdmin):
    list_display = ("question",)
    form = FaqAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


class ExternalSiteAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "title",
        "type",
    )
    form = ExternalSiteAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


class PublishedReportAdmin(RevisionCommentVersionAdmin):
    list_display = ("title",)
    form = PublishedReportAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


class DeploymentAdmin(RevisionCommentVersionAdmin):
    form = DeploymentAdminForm
    list_display = (
        "message_lt_display",
        "message_en_display",
        "level",
        "is_published",
        "start_date",
        "end_date",
    )
    list_editable = ("is_published",)

    def message_lt_display(self, obj):
        if obj.message_lt and len(obj.message_lt) >= 40:
            return obj.message_lt[:50] + "..."
        else:
            return obj.message_lt or ""

    message_lt_display.short_description = _("Pranešimas (lietuvių kalba)")

    def message_en_display(self, obj):
        if obj.message_en and len(obj.message_en) >= 40:
            return obj.message_en[:50] + "..."
        else:
            return obj.message_en or ""

    message_en_display.short_description = _("Pranešimas (anglų kalba)")


admin.site.register(LearningMaterial, LearningMaterialAdmin)
admin.site.register(Faq, FaqAdmin)
admin.site.register(ExternalSite, ExternalSiteAdmin)
admin.site.register(PublishedReport, PublishedReportAdmin)
admin.site.register(Deployment, DeploymentAdmin)


# The story post admin lives here, not in `vitrina.users`: `vitrina.users` has to be
# loaded before `cms`, but this admin has to be loaded after `djangocms_stories.admin`.
# `vitrina.cms` is listed after `djangocms_stories` in INSTALLED_APPS, so both hold.
admin.site.unregister(Post)


@admin.register(Post)
class CustomPostAdmin(OriginalPostAdmin):
    def has_module_permission(self, request):
        """Only Blog Administrators can see the blog section"""
        return request.user.has_perm("djangocms_stories.view_post")

    def has_add_permission(self, request):
        return request.user.has_perm("djangocms_stories.add_post")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("djangocms_stories.change_post")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("djangocms_stories.delete_post")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("djangocms_stories.view_post")
