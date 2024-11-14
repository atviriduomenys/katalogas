from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from vitrina.classifiers.forms import AreaOfManagementAdminForm
from vitrina.classifiers.models import Category, AreaOfManagement
from vitrina.classifiers.models import Licence
from vitrina.classifiers.models import Frequency
from vitrina.orgs.helpers import get_or_create_parent_org
from vitrina.orgs.models import Organization


class RootCategoryFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('kategoriją')

    parameter_name = 'root'

    def lookups(self, request, model_admin):
        for cat in Category.objects.filter(depth=1):
            yield (cat.id, cat.title)

    def queryset(self, request, queryset):
        cat_id = self.value()
        if cat_id:
            cat = Category.objects.get(id=cat_id)
            return queryset.filter(path__startswith=cat.path)


class CategoryAdmin(TreeAdmin):
    form = movenodeform_factory(Category)
    list_display = [
        'title',
        'numchild',
    ]
    list_filter = [
        RootCategoryFilter,
        'groups',
    ]
    search_fields = (
        'title',
    )


class LicenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_default',)
    fields = ('title', 'description', 'url', 'is_default',)

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            Licence.objects.filter(is_default=True).update(is_default=False)
        super().save_model(request, obj, form, change)


class FrequencyAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_default', 'hours')
    fields = ('title', 'title_en', 'hours', 'uri', 'is_default',)

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            Frequency.objects.filter(is_default=True).update(is_default=False)
        super().save_model(request, obj, form, change)


class AreaOfManagementAdmin(admin.ModelAdmin):
    form = AreaOfManagementAdminForm
    list_display = ('name_lt_verbose', 'organization_count')
    fields = ('name_lt', 'name_en', 'organizations')
    search_fields = ('name_lt', 'name_en')

    def get_organizations(self, obj):
        return ", ".join([org.name for org in obj.organization_set.all()])
    get_organizations.short_description = _('organizacijos')

    def organization_count(self, obj):
        return obj.organizations.count()
    organization_count.short_description = _('Priskirtų organizacijų kiekis')

    def name_lt_verbose(self, obj):
        return obj.name_lt
    name_lt_verbose.short_description = _('Pavadinimas')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        current_orgs = set(obj.organizations.all())
        new_orgs = set(form.cleaned_data.get('organizations', []))

        orgs_to_remove = current_orgs - new_orgs
        orgs_to_add = new_orgs - current_orgs

        if orgs_to_remove:
            self._remove_organizations(orgs_to_remove)
        if orgs_to_add:
            self._add_organizations(orgs_to_add, obj.pk)

        # Update organization name if area of management name is changed
        if ('name_lt' in form.changed_data and
                'name_lt' in form.initial and
                Organization.objects.filter(title=form.initial['name_lt']).exists()):
            organization = Organization.objects.get(title=form.initial['name_lt'])
            organization.title = obj.name_lt
            organization.save()

    def _remove_organizations(self, orgs_to_remove):
        for org in orgs_to_remove:
            org.jurisdiction_id = 1
            org.save()
            # Move node to unassigned (1)
            unassigned_area = AreaOfManagement.objects.get(id=1)
            org.move(Organization.objects.get(title=unassigned_area.name_lt), 'sorted-child')
            node = Organization.objects.get(pk=org.pk)
            node.save()
            # Update area of management organizations to unassigned (1)
            if not AreaOfManagement.organizations.through.objects.filter(
                    areaofmanagement_id=1,
                    organization_id=org.id
            ).exists():
                AreaOfManagement.organizations.through.objects.create(
                    areaofmanagement_id=1,
                    organization_id=org.id
                )
        Organization.fix_tree(fix_paths=True)

    def _add_organizations(self, orgs_to_add, obj):
        for org in orgs_to_add:
            # Unassign all organizations from this jurisdiction
            AreaOfManagement.organizations.through.objects.filter(organization_id=org.id).delete()
            # Update organization jurisdiction
            org.jurisdiction_id = obj
            org.save()
            # update hierarchy tree
            if org.jurisdiction_id != 1:
                parent_org = get_or_create_parent_org(obj)
                org.move(parent_org, 'sorted-child')
                node = Organization.objects.get(pk=org.pk)
                node.save()
        Organization.fix_tree(fix_paths=True)

    def delete_model(self, request, obj):
        self._remove_organizations(obj.organizations.all())
        super().delete_model(request, obj)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('organizations')

    def history_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = _("Valdymo srities koregavimo istorija")
        return super().history_view(request, object_id, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}

        extra_context.update({
            'title': _("Pridėti valdymo sritį"),
            'show_save_and_add_another': False,
            'show_save_and_continue': False
        })
        return super().add_view(request, form_url, extra_context)


admin.site.register(AreaOfManagement, AreaOfManagementAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Licence, LicenceAdmin)
admin.site.register(Frequency, FrequencyAdmin)
