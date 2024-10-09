import csv

import pytz
from django.contrib import admin, messages
from django.db.models import Value, F, Func, CharField, Case, When, OuterRef, Subquery
from django.db.models.functions import Concat, Substr
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from reversion.admin import VersionAdmin

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AuthenticationForm
from django.urls import reverse
from django.utils.html import format_html

from vitrina import settings
from vitrina.filters import FormatFilter
from vitrina.orgs.forms import RepresentativeRequestForm, TemplateForm
from vitrina.orgs.models import Representative, Template, OrganizationRepresentative

from vitrina.orgs.models import Organization, RepresentativeRequest
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.services import pre_representative_delete
from vitrina.structure.services import to_row
from vitrina.users.admin import AtTimeZone


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
    search_fields = ('title',)


class RepresentativeAdmin(admin.ModelAdmin):

    def delete_model(self, request, obj):
        pre_representative_delete(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            pre_representative_delete(obj)
        super().delete_queryset(request, queryset)


class OrganizationRepresentativeAdmin(admin.ModelAdmin):
    list_display = (
        'parent_organization_display',
        'organization_display',
        'full_name_display',
        'email',
        'role',
        'created_display',
        'status_display',
    )
    list_display_links = ('email',)
    actions = None
    search_fields = (
        'parent_organization_title',
        'organization_title',
        'full_name',
        'email',
        'role_title',
        'created_formatted',
        'status_title',
    )
    change_list_template = 'vitrina/orgs/admin/representative_change_list.html'
    list_filter = (FormatFilter,)

    def get_queryset(self, request):
        queryset = OrganizationRepresentative.objects_with_deleted.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)

        queryset = queryset.annotate(organization_title=Subquery(
            Organization.objects.filter(pk=OuterRef('object_id')).values_list('title', flat=True)
        ))
        queryset = queryset.annotate(organization_path=Subquery(
            Organization.objects.filter(pk=OuterRef('object_id')).values_list('path', flat=True)
        )).annotate(
            parent_path=Substr("organization_path", 1, Organization.steplen)
        ).annotate(parent_organization_title=Subquery(
            Organization.objects.filter(path=OuterRef('parent_path')).values_list('title', flat=True)
        ))
        queryset = queryset.annotate(full_name=Concat('user__first_name', Value(' '), 'user__last_name'))
        queryset = queryset.annotate(created_with_tz=AtTimeZone(F('created')))
        queryset = queryset.annotate(created_formatted=Func(
            F('created_with_tz'),
            Value('YYYY-MM-DD HH24:MI'),
            function='to_char',
            output_field=CharField()
        ))
        queryset = queryset.annotate(role_title=Case(
            When(role=OrganizationRepresentative.MANAGER, then=Value("Tvarkytojas")),
            When(role=OrganizationRepresentative.COORDINATOR, then=Value("Koordinatorius")),
            output_field=CharField(),
        ))
        queryset = queryset.annotate(status_title=Case(
            When(status=OrganizationRepresentative.ACTIVE, then=Value("Aktyvus")),
            When(status=OrganizationRepresentative.AWAITING_CONFIRMATION, then=Value("Laukiama patvirtinimo")),
            When(status=OrganizationRepresentative.DELETED, then=Value("Pašalintas")),
            output_field=CharField(),
        ))
        return queryset

    def parent_organization_display(self, obj):
        if obj.content_object:
            parent_organization = obj.content_object.get_root()
            if parent_organization:
                if len(parent_organization.title) >= 40:
                    title = parent_organization.title[:40] + "..."
                else:
                    title = parent_organization.title
                return title
        return "-"

    parent_organization_display.short_description = _('Tėvinė organizacija')
    parent_organization_display.admin_order_field = 'parent_organization_title'

    def organization_display(self, obj):
        if obj.content_object:
            organization = obj.content_object
            if len(organization.title) >= 40:
                title = organization.title[:40] + "..."
            else:
                title = organization.title
            return format_html('<a href="{}" target="_blank">{}</a>',
                               reverse('organization-members', args=[organization.pk]), title)
        return "-"

    organization_display.short_description = _('Organizacija')
    organization_display.admin_order_field = 'organization_title'

    def full_name_display(self, obj):
        if obj.user:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                reverse('admin:vitrina_users_user_change', args=[obj.user.pk]),
                f'{obj.user.first_name} {obj.user.last_name}'
            )
        return "-"

    full_name_display.short_description = _('Vardas ir pavardė')
    full_name_display.admin_order_field = 'full_name'

    def created_display(self, obj):
        if obj.created:
            tz = pytz.timezone(settings.TIME_ZONE)
            return obj.created.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"
    created_display.short_description = _("Sukurtas")
    created_display.admin_order_field = 'created'

    def status_display(self, obj):
        if obj.status:
            if obj.status == OrganizationRepresentative.ACTIVE:
                return format_html(
                    '<span style="color: limegreen;">{}</span>',
                    obj.get_status_display(),
                )
            elif obj.status == OrganizationRepresentative.AWAITING_CONFIRMATION:
                return format_html(
                    '<span style="color: orange;">{}</span>',
                    obj.get_status_display(),
                )
            elif obj.status == OrganizationRepresentative.DELETED:
                return format_html(
                    '<span style="color: red;">{}</span>',
                    obj.get_status_display(),
                )
        return "-"
    status_display.short_description = _("Būsena")
    status_display.admin_order_field = 'status'

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            'title': _("Organizacijos atstovų sąrašas")
        }
        result = super().changelist_view(request, extra_context)
        if request.GET.get('format') and request.GET.get('format') == 'csv':
            if change_list := result.context_data.get('cl'):
                stream = self._export_representative_list(change_list.queryset)
                result = StreamingHttpResponse(stream, content_type='text/csv')
                result['Content-Disposition'] = 'attachment; filename=Organizaciju atstovai.csv'
        elif result.context_data.get('cl'):
            result.context_data['cl'].has_filters = False
        return result

    def _export_representative_list(self, queryset):
        class _Stream(object):
            def write(self, value):
                return value

        cols = {
            'parent_organization': _("Tėvinė organizacija"),
            'organization': _("Organizacija"),
            'full_name': _("Vardas ir pavardė"),
            'email': _("Elektroninis paštas"),
            'role': _("Rolė"),
            'created': _("Sukurtas"),
            'status': _("Būsena"),
        }
        rows = self._get_representative(cols, queryset)
        rows = ({v: row[k] for k, v in cols.items()} for row in rows)

        stream = _Stream()
        yield stream.write(b'\xef\xbb\xbf')

        writer = csv.DictWriter(stream, fieldnames=cols.values(), delimiter=';')
        yield writer.writeheader()
        for row in rows:
            yield writer.writerow(row)

    def _get_representative(self, cols, queryset):
        for item in queryset:
            parent_organization = None
            if item.content_object:
                parent_organization = item.content_object.get_root()
            yield to_row(cols.keys(), {
                'parent_organization': parent_organization.title if parent_organization else "-",
                'organization': item.content_object.title if item.content_object else "-",
                'full_name': f'{item.user.first_name} {item.user.last_name}' if item.user else "-",
                'email': item.email,
                'role': item.get_role_display(),
                'created': self.created_display(item),
                'status': item.get_status_display(),
            })

    def delete_model(self, request, obj):
        pre_representative_delete(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            pre_representative_delete(obj)
        super().delete_queryset(request, queryset)


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Representative, RepresentativeAdmin)
admin.site.register(OrganizationRepresentative, OrganizationRepresentativeAdmin)


class RepresentativeRequestAdmin(admin.ModelAdmin):
    template_name = 'vitrina/orgs/approve.html'
    list_display = (
        'created_display',
        'user_display',
        'organization',
        'document_display',
        'phone',
        'email',
        'status',
        'account_actions_display',
    )
    list_display_links = None
    ordering = ('-created',)
    actions = None
    change_list_template = 'vitrina/orgs/admin/representative_request_change_list.html'
    change_form_template = 'vitrina/orgs/admin/representative_request_change_form.html'
    delete_confirmation_template = 'vitrina/orgs/admin/representative_request_delete_confirmation.html'
    form = RepresentativeRequestForm

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            'title': _('Duomenų tiekėjų prašymų sąrašas'),
            'template': Template.objects.filter(identifier=Template.REPRESENTATIVE_REQUEST_ID).first()
        }
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == RepresentativeRequest.CREATED:
            return True
        return False

    def has_module_permission(self, request):
        return True

    def user_display(self, obj):
        if obj.status == RepresentativeRequest.CREATED:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("supervisor_admin:vitrina_orgs_representativerequest_change", kwargs={'object_id': obj.id}),
                str(obj.user)
            )
        return str(obj.user)
    user_display.short_description = _('Naudotojas')
    user_display.admin_order_field = 'user'

    def document_display(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('partner-register-download', kwargs={'pk': obj.id}),
            obj.document.name
        )
    document_display.short_description = _('Pridėtas dokumentas')
    document_display.admin_order_field = 'document'

    def account_actions_display(self, obj):
        if obj.status == RepresentativeRequest.CREATED:
            return format_html(
                '<a class="button" href="{}">{}</a>&nbsp;'
                '<a class="button" href="{}">{}</a>',
                reverse('partner-register-approve', kwargs={'pk': obj.id}),
                _("Patvirtinti"),
                reverse('partner-register-deny', kwargs={'pk': obj.id}),
                _("Atmesti")
            )
        return ""
    account_actions_display.short_description = _('Veiksmai')
    account_actions_display.allow_tags = True
    account_actions_display.admin_order_field = 'status'

    def created_display(self, obj):
        timezone = pytz.timezone(settings.TIME_ZONE)
        return obj.created.astimezone(timezone).strftime("%Y-%m-%d %H:%M") if obj.created else "-"
    created_display.short_description = _('Sukurta')
    created_display.admin_order_field = 'created'

    def response_delete(self, request, obj_display, obj_id):
        self.message_user(
            request,
            _(f'"{obj_display}" prašymas pašalintas sėkmingai.'),
            messages.SUCCESS,
        )
        return redirect(reverse("supervisor_admin:vitrina_orgs_representativerequest_changelist"))

    def response_change(self, request, obj):
        msg = mark_safe(_(
            f'Duomenų tiekėjo "'
            f'<a href="{reverse("supervisor_admin:vitrina_orgs_representativerequest_change", args=[obj.pk])}">'
            f'{str(obj)}</a>" prašymas pakeistas sėkmingai.')
        )
        self.message_user(request, msg, messages.SUCCESS)
        return self.response_post_save_change(request, obj)


class TemplateAdmin(admin.ModelAdmin):
    change_form_template = 'vitrina/orgs/admin/template_change_form.html'
    object_history_template = 'vitrina/orgs/admin/template_history.html'
    form = TemplateForm

    def response_change(self, request, obj):
        msg = _('Šablonas pakeistas sėkmingai.')
        self.message_user(request, msg, messages.SUCCESS)
        return redirect(reverse("supervisor_admin:vitrina_orgs_representativerequest_changelist"))


class SupervisorAdminSite(AdminSite):
    """
    App-specific admin site implementation
    """

    login_form = AuthenticationForm
    site_header = 'Supervisor admin site'
    enable_nav_sidebar = False

    def has_permission(self, request):
        """
        Checks if the current user has access.
        """
        return request.user.is_supervisor or request.user.is_superuser


site = SupervisorAdminSite(name='supervisor_admin')
site.register(RepresentativeRequest, RepresentativeRequestAdmin)
site.register(Template, TemplateAdmin)
