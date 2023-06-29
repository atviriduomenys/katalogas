from django.contrib import admin
from parler.admin import TranslatableAdmin
from reversion.admin import VersionAdmin

import tagulous

from vitrina.datasets.models import Dataset, DatasetGroup, Attribution, DataServiceType, DataServiceSpecType, Type, Relation


class AttributionAdmin(admin.ModelAdmin):
    list_display = ('name', 'title',)


class DatasetAdmin(TranslatableAdmin, VersionAdmin):
    list_display = ('title', 'description', 'is_public')


class GroupAdmin(TranslatableAdmin):
    list_display = ('title',)


class DataServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('title',)


class DataServiceSpecTypeAdmin(admin.ModelAdmin):
    list_display = ('title',)


class TypeAdmin(TranslatableAdmin):
    list_display = ('title',)


class RelationAdmin(TranslatableAdmin):
    list_display = ('title',)


admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Attribution, AttributionAdmin)
admin.site.register(DatasetGroup, GroupAdmin)
admin.site.register(DataServiceType, DataServiceTypeAdmin)
admin.site.register(DataServiceSpecType, DataServiceSpecTypeAdmin)
admin.site.register(Type, TypeAdmin)
admin.site.register(Relation, RelationAdmin)

tagulous.admin.register(Dataset.tags)
