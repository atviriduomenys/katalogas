import secrets
from datetime import datetime

import pytz
from allauth.account.models import EmailAddress, EmailConfirmation, EmailConfirmationHMAC
from allauth.utils import build_absolute_uri
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from vitrina import settings
from vitrina.helpers import email
from vitrina.orgs.models import Organization
from vitrina.users.forms import RegisterAdminForm
from vitrina.users.models import User


class UserAdmin(BaseUserAdmin):
    list_display = (
        'created_display',
        'last_login_display',
        'organization_display',
        'name_display',
        'email',
        'status_display',
    )
    search_fields = ['first_name', 'last_name', 'email']
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'organization')
    ordering = ('first_name', 'last_name',)
    delete_confirmation_template = "vitrina/users/admin/delete_confirmation.html"
    delete_selected_confirmation_template = "vitrina/users/admin/delete_selected_confirmation.html"
    add_form = RegisterAdminForm
    add_form_template = "vitrina/users/admin/add_form.html"
    list_display_links = ('name_display',)

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

    def name_display(self, obj: User) -> str:
        return f'{obj.first_name} {obj.last_name}'

    name_display.short_description = _('Vardas ir pavardė')

    def organization_display(self, obj):
        reps = obj.representative_set.filter(
            content_type=ContentType.objects.get_for_model(Organization)
        )
        if len(reps) == 1:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                reps[0].content_object.get_absolute_url(),
                Truncator(reps[0].content_object).chars(42),
            )
        elif obj.organization:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.organization.get_absolute_url(),
                Truncator(obj.organization).chars(42),
            )
        else:
            return '-'
    organization_display.short_description = _("Organizacija")

    def created_display(self, obj):
        if obj.created:
            tz = pytz.timezone(settings.TIME_ZONE)
            return obj.created.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"
    created_display.short_description = _("Sukurtas")

    def last_login_display(self, obj):
        if obj.last_login:
            tz = pytz.timezone(settings.TIME_ZONE)
            return obj.last_login.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"
    last_login_display.short_description = _("Paskutinis prisijungimas")

    def status_display(self, obj):
        if obj.status:
            if obj.status == User.ACTIVE:
                return format_html(
                    '<span style="color: green;">{}</span>',
                    obj.get_status_display(),
                )
            elif obj.status == User.AWAITING_CONFIRMATION:
                return format_html(
                    '<span style="color: yellow;">{}</span>',
                    obj.get_status_display(),
                )
            elif obj.status == User.SUSPENDED:
                return format_html(
                    '<span style="color: red;">{}</span>',
                    obj.get_status_display(),
                )
            elif obj.status == User.DELETED:
                return format_html(
                    '<span style="color: red;">{}</span>',
                    obj.get_status_display(),
                )
        return "-"
    status_display.short_description = _("Būsena")

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

