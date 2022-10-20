from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Licence
from vitrina.classifiers.models import Frequency


class RootCategoryFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('kategoriją')

    parameter_name = 'root'

    def lookups(self, request, model_admin):
        for cat in Category.objects.filter(depth=1):
            yield (cat.id, cat.title)

    def queryset(self, request, queryset):
        cat_id = self.value()
        if cat_id:
            cat = Category.objects.get(id=cat_id)
            return queryset.filter(path__startswith=cat.path)


class CategoryAdmin(TreeAdmin):
    form = movenodeform_factory(Category)
    list_display = [
        'title',
        'numchild',
    ]
    list_filter = [
        RootCategoryFilter,
    ]
    search_fields = (
        'title',
    )


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


admin.site.register(Category, CategoryAdmin)
admin.site.register(Licence, LicenceAdmin)
admin.site.register(Frequency, FrequencyAdmin)
