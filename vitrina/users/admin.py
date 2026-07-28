import csv
from djangocms_blog.models import Post
from djangocms_blog.admin import PostAdmin as OriginalPostAdmin
import secrets
from datetime import datetime

import pytz
from allauth.account.models import (
    EmailAddress,
    EmailConfirmation,
    EmailConfirmationHMAC,
)
from allauth.utils import build_absolute_uri
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models import (
    Value,
    Case,
    When,
    CharField,
    Func,
    F,
    Count,
    Q,
    Subquery,
    OuterRef,
)
from django.db.models.functions import Concat
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from vitrina import settings
from vitrina.filters import FormatFilter
from vitrina.helpers import email
from vitrina.orgs.models import Organization, RepresentativeRequest, Representative
from vitrina.structure.services import to_row
from vitrina.users.forms import UserCreationAdminForm, UserChangeAdminForm
from vitrina.users.models import User
from vitrina.admin import RevisionCommentVersionAdmin


class AtTimeZone(Func):
    function = "AT TIME ZONE"
    template = f"(%(expressions)s %(function)s '{settings.TIME_ZONE}')"


class UserAdmin(BaseUserAdmin, RevisionCommentVersionAdmin):
    list_display = (
        "created_display",
        "last_login_display",
        "organization_display",
        "name_display",
        "email",
        "status_display",
    )
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "created_formatted",
        "last_login_formatted",
        "main_organization",
        "status_title",
    ]
    ordering = (
        "first_name",
        "last_name",
    )
    readonly_fields = ("viisp_company_code",)
    delete_confirmation_template = "vitrina/users/admin/delete_confirmation.html"
    change_list_template = "vitrina/users/admin/change_list.html"
    change_form_template = "vitrina/users/admin/change_form.html"
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm
    add_form_template = "vitrina/users/admin/add_form.html"
    list_display_links = ("name_display",)
    actions = None
    list_filter = (FormatFilter,)

    fieldsets = (
        (None, {"fields": ("user_status",)}),
        (
            _("Asmeninė informacija"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "email_confirmed",
                    "password1",
                    "password2",
                )
            },
        ),
        (_("Papildoma informacija"), {"fields": ("organizations_and_roles",)}),
        (
            _("Leidimai"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_viisp_login",
                    "viisp_company_code",
                    "groups",
                ),
            },
        ),
        (_("Svarbios datos"), {"fields": (("created_date", "last_login_date"),)}),
    )
    fieldsets_without_orgs = (
        (None, {"fields": ("user_status",)}),
        (
            _("Asmeninė informacija"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "email_confirmed",
                    "password1",
                    "password2",
                )
            },
        ),
        (
            _("Leidimai"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_viisp_login",
                    "viisp_company_code",
                    "groups",
                ),
            },
        ),
        (_("Svarbios datos"), {"fields": (("created_date", "last_login_date"),)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    filter_horizontal = ("groups",)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        elif obj.representative_set.filter(content_type=ContentType.objects.get_for_model(Organization)):
            return self.fieldsets
        else:
            return self.fieldsets_without_orgs

    def get_queryset(self, request):
        queryset = User.objects_with_deleted.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)

        queryset = queryset.annotate(full_name=Concat("first_name", Value(" "), "last_name"))
        queryset = queryset.annotate(created_with_tz=AtTimeZone(F("created")))
        queryset = queryset.annotate(
            created_formatted=Func(
                F("created_with_tz"),
                Value("YYYY-MM-DD HH24:MI"),
                function="to_char",
                output_field=CharField(),
            )
        )
        queryset = queryset.annotate(last_login_with_tz=AtTimeZone(F("last_login")))
        queryset = queryset.annotate(
            last_login_formatted=Func(
                F("last_login_with_tz"),
                Value("YYYY-MM-DD HH24:MI"),
                function="to_char",
                output_field=CharField(),
            )
        )
        queryset = queryset.annotate(
            status_title=Case(
                When(status=User.ACTIVE, then=Value("Aktyvus")),
                When(
                    status=User.AWAITING_CONFIRMATION,
                    then=Value("Laukiama patvirtinimo"),
                ),
                When(status=User.SUSPENDED, then=Value("Suspenduotas")),
                When(status=User.DELETED, then=Value("Pašalintas")),
                When(status=User.LOCKED, then=Value("Užrakintas")),
                output_field=CharField(),
            )
        )
        queryset = queryset.annotate(
            organization_rep_count=Count(
                "representative__pk",
                filter=Q(representative__content_type=ContentType.objects.get_for_model(Organization)),
            )
        )
        queryset = queryset.annotate(
            main_organization=Case(
                When(
                    organization_rep_count=1,
                    then=Subquery(Organization.objects.filter(representatives__user_id=OuterRef("pk")).values("title")),
                ),
                default=F("organization__title"),
            )
        )
        return queryset

    def name_display(self, obj: User) -> str:
        return f"{obj.first_name} {obj.last_name}"

    name_display.short_description = _("Vardas ir pavardė")
    name_display.admin_order_field = "full_name"

    def organization_display(self, obj):
        reps = obj.representative_set.filter(content_type=ContentType.objects.get_for_model(Organization))
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
            return "-"

    organization_display.short_description = _("Organizacija")
    organization_display.admin_order_field = "main_organization"

    def created_display(self, obj):
        if obj.created:
            tz = pytz.timezone(settings.TIME_ZONE)
            return obj.created.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"

    created_display.short_description = _("Sukurtas")
    created_display.admin_order_field = "created"

    def last_login_display(self, obj):
        if obj.last_login:
            tz = pytz.timezone(settings.TIME_ZONE)
            return obj.last_login.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"

    last_login_display.short_description = _("Paskutinis prisijungimas")
    last_login_display.admin_order_field = "last_login"

    def status_display(self, obj):
        if obj.status:
            if obj.status == User.ACTIVE:
                return format_html(
                    '<span style="color: limegreen;">{}</span>',
                    obj.get_status_display(),
                )
            elif obj.status == User.AWAITING_CONFIRMATION:
                return format_html(
                    '<span style="color: orange;">{}</span>',
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
            elif obj.status == User.LOCKED:
                return format_html(
                    '<span style="color: grey;">{}</span>',
                    obj.get_status_display(),
                )
        return "-"

    status_display.short_description = _("Būsena")
    status_display.admin_order_field = "status"

    def add_view(self, request, form_url="", extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update(
            {
                "title": _("Sukurti naują naudotoją"),
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
            }
        )
        return super().add_view(request, form_url, extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        email_address = EmailAddress.objects.create(user=obj, email=obj.email, primary=True, verified=False)
        EmailConfirmation.objects.create(
            created=datetime.now(),
            sent=datetime.now(),
            key=secrets.token_urlsafe(),
            email_address=email_address,
        )
        confirmation = EmailConfirmationHMAC(email_address)
        url = reverse("account_confirm_email", args=[confirmation.key])
        activate_url = build_absolute_uri(request, url)
        email(
            [email_address.email],
            "confirm_email",
            "vitrina/email/confirm_email.md",
            {
                "site": Site.objects.get_current().domain,
                "user": str(obj),
                "activate_url": activate_url,
            },
        )

        # update related representatives
        if reps := Representative.objects.filter(email=obj.email, user__isnull=True):
            reps.update(user=obj)

        return super().response_add(request, obj, post_url_continue)

    def changelist_view(self, request, extra_context=None):
        extra_context = {"title": _("Naudotojų sąrašas")}
        result = super().changelist_view(request, extra_context)
        if request.GET.get("format") and request.GET.get("format") == "csv":
            if change_list := result.context_data.get("cl"):
                stream = self._export_user_list(change_list.queryset)
                result = StreamingHttpResponse(stream, content_type="text/csv")
                result["Content-Disposition"] = "attachment; filename=Naudotojai.csv"
        elif result.context_data.get("cl"):
            result.context_data["cl"].has_filters = False
        return result

    def _export_user_list(self, queryset):
        class _Stream(object):
            def write(self, value):
                return value

        cols = {
            "created": _("Sukurtas"),
            "last_login": _("Paskutinis prisijungimas"),
            "organization": _("Organizacija"),
            "full_name": _("Vardas ir pavardė"),
            "email": _("Elektroninis paštas"),
            "status": _("Būsena"),
        }
        rows = self._get_user(cols, queryset)
        rows = ({v: row[k] for k, v in cols.items()} for row in rows)

        stream = _Stream()
        yield stream.write(b"\xef\xbb\xbf")

        writer = csv.DictWriter(stream, fieldnames=cols.values(), delimiter=";")
        yield writer.writeheader()
        for row in rows:
            yield writer.writerow(row)

    def _get_user(self, cols, queryset):
        for item in queryset:
            reps = item.representative_set.filter(content_type=ContentType.objects.get_for_model(Organization))
            if len(reps) == 1:
                organization = reps[0].content_object
            else:
                organization = item.organization
            yield to_row(
                cols.keys(),
                {
                    "created": self.created_display(item),
                    "last_login": self.last_login_display(item),
                    "organization": organization.title if organization else "-",
                    "full_name": self.name_display(item),
                    "email": item.email,
                    "status": item.get_status_display() if item.status else "-",
                },
            )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {"title": "", "subtitle": _("Redaguoti naudotoją")}
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        msg = format_html(
            _('Naudotojas "<a href="{url}">{obj}</a>" pakeistas sėkmingai.'),
            url=reverse("admin:vitrina_users_user_change", args=[obj.pk]),
            obj=str(obj),
        )
        self.message_user(request, msg, messages.SUCCESS)
        return self.response_post_save_change(request, obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            if "email" in form.changed_data:
                if existing_email_address := EmailAddress.objects.filter(user=obj):
                    existing_email_address.delete()
                email_address = EmailAddress.objects.create(user=obj, email=obj.email, primary=True, verified=False)
                EmailConfirmation.objects.create(
                    created=datetime.now(),
                    sent=datetime.now(),
                    key=secrets.token_urlsafe(),
                    email_address=email_address,
                )
                confirmation = EmailConfirmationHMAC(email_address)
                url = reverse("account_confirm_email", args=[confirmation.key])
                activate_url = build_absolute_uri(request, url)
                email(
                    [email_address.email],
                    "confirm_updated_email",
                    "vitrina/email/confirm_updated_email.md",
                    {
                        "site": Site.objects.get_current().domain,
                        "user": str(obj),
                        "activate_url": activate_url,
                    },
                )
                obj.status = User.AWAITING_CONFIRMATION
                obj.representative_set.update(email=obj.email)

            elif "email_confirmed" in form.changed_data:
                email_confirmed = form.cleaned_data.get("email_confirmed", False)
                obj.status = User.ACTIVE if email_confirmed else User.AWAITING_CONFIRMATION

                email_address = EmailAddress.objects.filter(user=obj, email=obj.email).first()
                if email_address:
                    email_address.verified = email_confirmed
                    email_address.save()
                else:
                    EmailAddress.objects.create(user=obj, email=obj.email, primary=True, verified=False)

            if "is_active" in form.changed_data:
                is_active = form.cleaned_data.get("is_active", False)
                email_confirmed = form.cleaned_data.get("email_confirmed", False)
                if is_active and email_confirmed:
                    obj.status = User.ACTIVE
                elif is_active:
                    obj.status = User.AWAITING_CONFIRMATION
                else:
                    obj.status = User.SUSPENDED

            obj.save()

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        reps = []
        for rep in obj.representative_set.all():
            if isinstance(rep.content_object, Organization):
                rep_display = format_html(
                    _('Organizacijos "{obj}" {role}: <a href="{url}">{email}</a>'),
                    obj=rep.content_object,
                    role=rep.get_role_display().lower(),
                    url=reverse("admin:vitrina_orgs_representative_change", args=[rep.pk]),
                    email=rep.email,
                )
            else:
                rep_display = format_html(
                    _('Duomenų ištekliaus "{obj}" {role}: <a href="{url}">{email}</a>'),
                    obj=rep.content_object,
                    role=rep.get_role_display().lower(),
                    url=reverse("admin:vitrina_orgs_representative_change", args=[rep.pk]),
                    email=rep.email,
                )
            reps.append(rep_display)

        extra_context = {"protected": reps}
        return super().delete_view(request, object_id, extra_context)

    def delete_model(self, request, obj):
        EmailAddress.objects.filter(user=obj).delete()
        obj.subscription_set.all().delete()
        obj.representativerequest_set.filter(status=RepresentativeRequest.CREATED).update(
            status=RepresentativeRequest.REJECTED
        )

        obj.deleted = True
        obj.deleted_on = timezone.now()
        obj.status = User.DELETED
        obj.save()

    def response_delete(self, request, obj_display, obj_id):
        msg = format_html(
            _('Naudotojas "<a href="{url}">{obj}</a>" pašalintas sėkmingai.'),
            url=reverse("admin:vitrina_users_user_change", args=[obj_id]),
            obj=str(obj_display),
        )
        self.message_user(request, msg, messages.SUCCESS)
        return redirect(reverse("admin:vitrina_users_user_changelist"))


# Unregister the original `django-cms` blog post admin.
admin.site.unregister(Post)


@admin.register(Post)
class CustomPostAdmin(OriginalPostAdmin):
    def has_module_permission(self, request):
        """Only Blog Administrators can see the blog section"""
        return request.user.has_perm("djangocms_blog.view_post")

    def has_add_permission(self, request):
        return request.user.has_perm("djangocms_blog.add_post")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("djangocms_blog.change_post")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("djangocms_blog.delete_post")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("djangocms_blog.view_post")


admin.site.unregister(EmailAddress)
admin.site.register(User, UserAdmin)
