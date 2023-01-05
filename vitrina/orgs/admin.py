from django.contrib import admin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from vitrina.orgs.models import Organization


class OrganizationAdmin(TreeAdmin):
    list_filter = ('jurisdiction',)
    form = movenodeform_factory(Organization)


admin.site.register(Organization, OrganizationAdmin)
