import pytz
from django.contrib import admin, messages
from django.shortcuts import redirect
from reversion.admin import VersionAdmin

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AuthenticationForm
from django.urls import reverse
from django.utils.html import format_html

from vitrina import settings
from vitrina.orgs.forms import RepresentativeRequestForm, TemplateForm
from vitrina.orgs.models import Representative, Template

from vitrina.orgs.models import Organization, RepresentativeRequest
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.services import pre_representative_delete


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


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Representative, RepresentativeAdmin)


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
