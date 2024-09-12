import secrets
from datetime import datetime

from allauth.account.models import EmailAddress, EmailConfirmation, EmailConfirmationHMAC
from allauth.utils import build_absolute_uri
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from vitrina.helpers import email
from vitrina.users.forms import RegisterAdminForm
from vitrina.users.models import User


class UserAdmin(BaseUserAdmin):
    list_display = ('name', 'org', 'last_login', 'is_staff')
    search_fields = ['first_name', 'last_name', 'email']
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'organization')
    ordering = ('email',)
    delete_confirmation_template = "vitrina/users/admin/delete_confirmation.html"
    delete_selected_confirmation_template = "vitrina/users/admin/delete_selected_confirmation.html"
    add_form = RegisterAdminForm
    add_form_template = "vitrina/users/admin/add_form.html"

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Asmeninė informacija'), {'fields': ('first_name', 'last_name', 'organization')}),
        (_('Leidimai'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Svarbios datos'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
    )

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

    def add_view(self, request, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update({
            'title': _("Sukurti naują naudotoją"),
            'show_save_and_add_another': False,
            'show_save_and_continue': False
        })
        return super().add_view(request, form_url, extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        email_address = EmailAddress.objects.create(user=obj, email=obj.email, primary=True, verified=False)
        EmailConfirmation.objects.create(
            created=datetime.now(),
            sent=datetime.now(),
            key=secrets.token_urlsafe(),
            email_address=email_address
        )
        confirmation = EmailConfirmationHMAC(email_address)
        url = reverse("account_confirm_email", args=[confirmation.key])
        activate_url = build_absolute_uri(request, url)
        email(
            [email_address.email], 'confirm_email', 'vitrina/email/confirm_email.md',
            {
                'site': Site.objects.get_current().domain,
                'user': str(obj),
                'activate_url': activate_url
            }
        )

        return super().response_add(request, obj, post_url_continue)


admin.site.register(User, UserAdmin)

