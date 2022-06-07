from django.contrib import admin

from vitrina.datasets.models import Organization


class OrganizationAdmin(admin.ModelAdmin):
    list_filter = ('jurisdiction',)


admin.site.register(Organization, OrganizationAdmin)
