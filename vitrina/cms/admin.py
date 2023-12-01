from django.contrib import admin

from vitrina.cms.forms import LearningMaterialAdminForm, FaqAdminForm, ExternalSiteAdminForm, PublishedReportAdminForm
from vitrina.cms.models import LearningMaterial, Faq, ExternalSite
from vitrina.orgs.models import PublishedReport


class LearningMaterialAdmin(admin.ModelAdmin):
    list_display = ('topic', 'published',)
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
    list_display = ('question',)
    form = FaqAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


class ExternalSiteAdmin(admin.ModelAdmin):
    list_display = ('title', 'type',)
    form = ExternalSiteAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


class PublishedReportAdmin(admin.ModelAdmin):
    list_display = ('title',)
    form = PublishedReportAdminForm

    def save_model(self, request, obj, form, change):
        if obj.version:
            obj.version += 1
        else:
            obj.version = 1

        super().save_model(request, obj, form, change)


admin.site.register(LearningMaterial, LearningMaterialAdmin)
admin.site.register(Faq, FaqAdmin)
admin.site.register(ExternalSite, ExternalSiteAdmin)
admin.site.register(PublishedReport, PublishedReportAdmin)
