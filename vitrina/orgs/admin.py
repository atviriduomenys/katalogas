from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from reversion.admin import VersionAdmin

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AuthenticationForm
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import render
from django.template.loader import render_to_string


from vitrina.orgs.models import Organization, RepresentativeRequest


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

class RepresentativeRequestAdmin(admin.ModelAdmin):
    template_name = 'vitrina/orgs/approve.html'
    list_display = (
        'user',
        'document',
        'org_code',
        'org_name',
        'org_slug', 
        'account_actions',
    )

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_module_permission(self, request):
        return True

    def account_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Confirm</a>&nbsp;'
            '<a class="button" href="{}">Deny</a>',
            reverse('partner-register-approve', kwargs={'pk': obj.id}),
            reverse('partner-register-deny', kwargs={'pk': obj.id}),
        )
    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

class SupervisorAdminSite(AdminSite):
    """
    App-specific admin site implementation
    """

    login_form = AuthenticationForm
    site_header = 'Supervisor admin site'

    def has_permission(self, request):
        """
        Checks if the current user has access.
        """
        return request.user.is_supervisor or request.user.is_superuser

site = SupervisorAdminSite(name='myadmin')
site.register(RepresentativeRequest, RepresentativeRequestAdmin)