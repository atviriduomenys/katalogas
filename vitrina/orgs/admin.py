import pytz
from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.shortcuts import redirect
from django.utils.safestring import mark_safe

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AuthenticationForm
from django.urls import reverse
from django.utils.html import format_html

from vitrina import settings
from vitrina.datasets.models import Dataset
from vitrina.orgs.forms import (
    RepresentativeRequestForm,
    TemplateForm,
    AdminPublisherOrganizationForm,
    AdminPublisherAssignedOrganizationForm,
    WhitelistedCodeNameInlineForm,
)
from vitrina.orgs.models import Representative, Template, WhitelistedCodeName

from vitrina.orgs.models import (
    Organization,
    RepresentativeRequest,
    PublisherOrganization,
)
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.services import pre_representative_delete, remove_representative_subscription
from vitrina.admin import RevisionCommentVersionAdmin


class RootOrganizationFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("organizacija")

    parameter_name = "root"

    def lookups(self, request, model_admin):
        for org in Organization.objects.filter(depth=1):
            yield (org.id, org.title)

    def queryset(self, request, queryset):
        org_id = self.value()
        if org_id:
            org = Organization.objects.get(id=org_id)
            return queryset.filter(path__startswith=org.path)


class WhitelistedCodeNameInline(admin.TabularInline):
    model = WhitelistedCodeName
    form = WhitelistedCodeNameInlineForm
    extra = 1
    fields = ["code_name"]
    verbose_name = _("Leistinas kodinis pavadinimas")
    verbose_name_plural = _("Leistini kodiniai pavadinimai")

    def has_add_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return request.user.is_staff or request.user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return request.user.is_staff or request.user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return request.user.is_staff or request.user.is_superuser


class OrganizationAdmin(RevisionCommentVersionAdmin, TreeAdmin):
    form = movenodeform_factory(Organization)
    list_display = [
        "title",
        "numchild",
    ]
    list_filter = (RootOrganizationFilter,)
    inlines = [WhitelistedCodeNameInline]
    search_fields = ("title",)

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("vitrina_orgs.view_organization")

    def has_add_permission(self, request):
        return request.user.has_perm("vitrina_orgs.add_organization")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("vitrina_orgs.change_organization")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("vitrina_orgs.delete_organization")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))

        if request.user.has_perm("vitrina_orgs.view_organization") and not request.user.has_perm(
            "vitrina_orgs.change_organization"
        ):
            readonly_fields.extend([field.name for field in self.model._meta.fields])

        return readonly_fields


class RepresentativeAdmin(RevisionCommentVersionAdmin):
    search_fields = ("email",)
    readonly_fields = ("can_make_agreements",)

    def delete_model(self, request, obj):
        remove_representative_subscription(obj)
        pre_representative_delete(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            remove_representative_subscription(obj)
            pre_representative_delete(obj)
        super().delete_queryset(request, queryset)


class PublisherAdmin(RevisionCommentVersionAdmin):
    list_display = ["title"]
    search_fields = ("title",)
    actions = ["remove_publisher_status"]
    change_form_template = "vitrina/orgs/admin/organization_publisher_change_form.html"
    form = AdminPublisherAssignedOrganizationForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(publisher=True)

    def save_model(self, request, obj, form, change):
        if request.path == "/admin/vitrina_orgs/publisherorganization/add/":
            obj.publisher = True
        obj.save()

        if not change:
            return

        self._update_assignments(
            obj,
            set(form.cleaned_data["datasets"].values_list("id", flat=True)),
            Dataset,
            Representative.OPEN_DATA_MANAGER,
        )

        self._update_assignments(
            obj,
            set(form.cleaned_data["creator_assignment"].values_list("id", flat=True)),
            Organization,
            Representative.OPEN_DATA_MANAGER,
        )

    def _update_assignments(self, obj, new_assignments, model, role):
        content_type = ContentType.objects.get_for_model(model)
        current_assignments = set(
            model.objects.filter(
                pk__in=Representative.objects.filter(content_type=content_type, organization=obj).values_list(
                    "object_id", flat=True
                )
            ).values_list("id", flat=True)
        )

        removed_assignments = current_assignments - new_assignments
        added_assignments = new_assignments - current_assignments

        if removed_assignments:
            self._handle_removed_assignments(content_type, model, obj, removed_assignments)

        if added_assignments:
            self._handle_added_assignments(content_type, model, obj, added_assignments, role)

    @staticmethod
    def _handle_removed_assignments(content_type, model, obj, removed_assignments):
        Representative.objects.filter(
            content_type=content_type,
            object_id__in=[item.id if isinstance(item, model) else item for item in removed_assignments],
            organization=obj,
        ).delete()

        for assignment in removed_assignments:
            if isinstance(assignment, model):
                assignment = assignment.pk
            if model == Dataset:
                assignment = Dataset.objects.get(pk=assignment)
                assignment.publisher = None
                assignment.save()

    @staticmethod
    def _handle_added_assignments(content_type, model, obj, added_assignments, role):
        for assignment in added_assignments:
            if isinstance(assignment, model):
                assignment = assignment.pk
            Representative.objects.get_or_create(
                content_type=content_type,
                object_id=assignment,
                organization=obj,
                role=role,
            )
            if model == Dataset:
                assignment = Dataset.objects.get(pk=assignment)
                assignment.publisher = obj
                assignment.save()

    def delete_model(self, request, obj):
        obj.publisher = False
        obj.save()

    def remove_publisher_status(self, request, queryset):
        queryset.update(publisher=False)
        self.message_user(
            request,
            _("Pasirinktoms organizacijoms sėkmingai pašalintas, duomenų atvėrimo paslaugos teikėjo rolė."),
            messages.SUCCESS,
        )

    remove_publisher_status.short_description = _("Pašalinti duomenų atvėrimo paslaugos teikėjo rolę")

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def save_related(self, request, form, formsets, change):
        pass

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = _("Duomenų atvėrimo paslaugos teikėjai")
        extra_context["add_button_label"] = _("Priskirti duomenų atvėrimo paslaugos teikėjo rolę")
        return super().changelist_view(request, extra_context=extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = _("Redaguoti duomenų atvėrimo paslaugos teikėją")
        extra_context["show_save_and_add_another"] = False
        extra_context["show_save_and_continue"] = False
        extra_context["publisher_id"] = object_id

        return super().changeform_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(
            {
                "title": _("Suteikti duomenų atvėrimo paslaugos teikėjo rolę"),
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
            }
        )
        return super().add_view(request, form_url, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        if request.path == "/admin/vitrina_orgs/publisherorganization/add/":
            kwargs["form"] = AdminPublisherOrganizationForm
        return super().get_form(request, obj, **kwargs)


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(PublisherOrganization, PublisherAdmin)
admin.site.register(Representative, RepresentativeAdmin)


class RepresentativeRequestAdmin(admin.ModelAdmin):
    template_name = "vitrina/orgs/approve.html"
    list_display = (
        "created_display",
        "user_display",
        "organization",
        "document_display",
        "phone",
        "email",
        "status",
        "account_actions_display",
    )
    list_display_links = None
    ordering = ("-created",)
    actions = None
    change_list_template = "vitrina/orgs/admin/representative_request_change_list.html"
    change_form_template = "vitrina/orgs/admin/representative_request_change_form.html"
    delete_confirmation_template = "vitrina/orgs/admin/representative_request_delete_confirmation.html"
    form = RepresentativeRequestForm

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            "title": _("Duomenų teikėjų prašymų sąrašas"),
            "template": Template.objects.filter(identifier=Template.REPRESENTATIVE_REQUEST_ID).first(),
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
                reverse(
                    "supervisor_admin:vitrina_orgs_representativerequest_change",
                    kwargs={"object_id": obj.id},
                ),
                str(obj.user),
            )
        return str(obj.user)

    user_display.short_description = _("Naudotojas")
    user_display.admin_order_field = "user"

    def document_display(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("partner-register-download", kwargs={"pk": obj.id}),
            obj.document.name,
        )

    document_display.short_description = _("Pridėtas dokumentas")
    document_display.admin_order_field = "document"

    def account_actions_display(self, obj):
        if obj.status == RepresentativeRequest.CREATED:
            return format_html(
                '<a class="button" href="{}">{}</a>&nbsp;<a class="button" href="{}">{}</a>',
                reverse("partner-register-approve", kwargs={"pk": obj.id}),
                _("Patvirtinti"),
                reverse("partner-register-deny", kwargs={"pk": obj.id}),
                _("Atmesti"),
            )
        return ""

    account_actions_display.short_description = _("Veiksmai")
    account_actions_display.allow_tags = True
    account_actions_display.admin_order_field = "status"

    def created_display(self, obj):
        timezone = pytz.timezone(settings.TIME_ZONE)
        return obj.created.astimezone(timezone).strftime("%Y-%m-%d %H:%M") if obj.created else "-"

    created_display.short_description = _("Sukurta")
    created_display.admin_order_field = "created"

    def response_delete(self, request, obj_display, obj_id):
        self.message_user(
            request,
            _(f'"{obj_display}" prašymas pašalintas sėkmingai.'),
            messages.SUCCESS,
        )
        return redirect(reverse("supervisor_admin:vitrina_orgs_representativerequest_changelist"))

    def response_change(self, request, obj):
        msg = mark_safe(
            _(
                f'Duomenų teikėjo "'
                f'<a href="{reverse("supervisor_admin:vitrina_orgs_representativerequest_change", args=[obj.pk])}">'
                f'{str(obj)}</a>" prašymas pakeistas sėkmingai.'
            )
        )
        self.message_user(request, msg, messages.SUCCESS)
        return self.response_post_save_change(request, obj)


class TemplateAdmin(admin.ModelAdmin):
    change_form_template = "vitrina/orgs/admin/template_change_form.html"
    object_history_template = "vitrina/orgs/admin/template_history.html"
    form = TemplateForm

    def response_change(self, request, obj):
        msg = _("Šablonas pakeistas sėkmingai.")
        self.message_user(request, msg, messages.SUCCESS)
        return redirect(reverse("supervisor_admin:vitrina_orgs_representativerequest_changelist"))


class SupervisorAdminSite(AdminSite):
    """
    App-specific admin site implementation
    """

    login_form = AuthenticationForm
    site_header = "Supervisor admin site"
    enable_nav_sidebar = False

    def has_permission(self, request):
        """
        Checks if the current user has access.
        """
        return request.user.is_supervisor or request.user.is_superuser


site = SupervisorAdminSite(name="supervisor_admin")
site.register(RepresentativeRequest, RepresentativeRequestAdmin)
site.register(Template, TemplateAdmin)
