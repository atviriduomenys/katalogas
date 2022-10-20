from django.contrib import admin

import tagulous

from vitrina.datasets.models import Dataset


class DatasetAdmin(admin.ModelAdmin):
    list_filter = ('organization',)


admin.site.register(Dataset, DatasetAdmin)

tagulous.admin.register(Dataset.tags)
