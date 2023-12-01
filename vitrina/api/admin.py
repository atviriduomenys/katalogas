from django.contrib import admin
from reversion.admin import VersionAdmin

from vitrina.api.models import ApiKey, ApiScope
from django.utils.translation import gettext_lazy as _


class ClientIdFilter(admin.SimpleListFilter):
    title = _('kliento id')
    parameter_name = 'client_id'
    default_value = None

    def lookups(self, request, model_admin):
        return [
            ('organization_null', _('Nepriskirti')),
        ]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset.filter(client_id__isnull=False)
        else:
            return queryset.filter(organization__isnull=True, client_id__isnull=False)


class ApiScopeInline(admin.TabularInline):
    model = ApiScope


class ApiKeyAdmin(VersionAdmin):
    list_display = ('organization', 'client_id', 'client_name')
    list_filter = [ClientIdFilter]
    search_fields = (
        'organization',
    )
    # inlines = [ApiScopeInline]


admin.site.register(ApiKey, ApiKeyAdmin)
