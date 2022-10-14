from django.contrib import admin

from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Licence
from vitrina.classifiers.models import Frequency


class LicenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_default',)
    fields = ('title', 'description', 'url', 'is_default',)

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            Licence.objects.filter(is_default=True).update(is_default=False)
        super().save_model(request, obj, form, change)


class FrequencyAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_default',)
    fields = ('title', 'title_en', 'uri', 'is_default',)

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            Frequency.objects.filter(is_default=True).update(is_default=False)
        super().save_model(request, obj, form, change)


admin.site.register(Category)
admin.site.register(Licence, LicenceAdmin)
admin.site.register(Frequency, FrequencyAdmin)
