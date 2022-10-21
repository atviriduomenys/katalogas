from django.contrib import admin
from reversion.admin import VersionAdmin

import tagulous

from vitrina.datasets.models import Dataset


class DatasetAdmin(VersionAdmin):
    list_filter = ('organization',)


admin.site.register(Dataset, DatasetAdmin)

tagulous.admin.register(Dataset.tags)
