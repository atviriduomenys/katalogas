from django.contrib import admin
from parler.admin import TranslatableAdmin
from reversion.admin import VersionAdmin

import tagulous

from vitrina.datasets.models import Dataset, DatasetGroup


class DatasetAdmin(TranslatableAdmin, VersionAdmin):
    list_display = ('title', 'description', 'is_public')


class GroupAdmin(admin.ModelAdmin):
    list_display = ('title',)


admin.site.register(Dataset, DatasetAdmin)
admin.site.register(DatasetGroup, GroupAdmin)

tagulous.admin.register(Dataset.tags)
