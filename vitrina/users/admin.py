from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.text import Truncator

from vitrina.users.models import User


class UserAdmin(BaseUserAdmin):
    list_display = ('name', 'org', 'last_login', 'is_staff')
    search_fields = ['first_name', 'last_name', 'email']
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'organization')
    ordering = ('email',)

    @admin.display()
    def name(self, obj: User) -> str:
        return f'{obj.first_name} {obj.last_name}'

    @admin.display()
    def org(self, obj):
        if obj.organization:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.organization.get_absolute_url(),
                Truncator(obj.organization).chars(42),
            )
        else:
            return ''


admin.site.register(User, UserAdmin)
