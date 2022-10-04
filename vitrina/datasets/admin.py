from django.contrib import admin
from parler.admin import TranslatableAdmin

from vitrina.datasets.models import Dataset


class DatasetAdmin(TranslatableAdmin):
    list_display = ('title', 'description', 'is_public')
    list_filter = ('organization',)


admin.site.register(Dataset, DatasetAdmin)
