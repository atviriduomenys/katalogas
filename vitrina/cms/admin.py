from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from vitrina.cms.forms import (
    LearningMaterialAdminForm,
    FaqAdminForm,
    ExternalSiteAdminForm,
    PublishedReportAdminForm,
)
from vitrina.cms.models import LearningMaterial, Faq, ExternalSite, Deployment
from vitrina.orgs.models import PublishedReport


class LearningMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "topic",
        "published",
    )
    form = LearningMaterialAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1
        if not obj.user:
            obj.user = request.user

        super().save_model(request, obj, form, change)


class FaqAdmin(admin.ModelAdmin):
    list_display = ("question",)
    form = FaqAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


class ExternalSiteAdmin(admin.ModelAdmin):
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


class PublishedReportAdmin(admin.ModelAdmin):
    list_display = ("title",)
    form = PublishedReportAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


class DeploymentAdmin(admin.ModelAdmin):
    list_display = (
        'message_lt_display',
        'message_en_display',
        'start_date',
        'end_date',
    )

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
