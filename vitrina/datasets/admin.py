from django.contrib import admin
from parler.admin import TranslatableAdmin
from reversion.admin import VersionAdmin

import tagulous

from vitrina.datasets.models import Dataset


class DatasetAdmin(TranslatableAdmin, VersionAdmin):
    list_display = ('title', 'description', 'is_public')


admin.site.register(Dataset, DatasetAdmin)

tagulous.admin.register(Dataset.tags)
