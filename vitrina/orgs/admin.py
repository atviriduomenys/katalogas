from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from reversion.admin import VersionAdmin

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from vitrina.orgs.models import Organization


class RootOrganizationFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('organizacija')

    parameter_name = 'root'

    def lookups(self, request, model_admin):
        for org in Organization.objects.filter(depth=1):
            yield (org.id, org.title)

    def queryset(self, request, queryset):
        org_id = self.value()
        if org_id:
            org = Organization.objects.get(id=org_id)
            return queryset.filter(path__startswith=org.path)


class OrganizationAdmin(VersionAdmin, TreeAdmin):
    form = movenodeform_factory(Organization)
    list_display = ['title', 'numchild',]
    list_filter = (RootOrganizationFilter,)
    form = movenodeform_factory(Organization)
    search_fields = ('title',)


admin.site.register(Organization, OrganizationAdmin)
