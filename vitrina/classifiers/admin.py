from typing import Any
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from parler.admin import TranslatableAdmin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from vitrina.classifiers.forms import AreaOfManagementAdminForm
from vitrina.classifiers.models import (
    Category,
    AreaOfManagement,
    GeoportalCategory,
    GeoportalFrequency,
    Status,
    Concept,
    ConceptSchema,
    ApplicableLegislation,
)
from vitrina.classifiers.models import Licence
from vitrina.classifiers.models import Frequency
from vitrina.datasets.models import DatasetGroupCategoryUri
from vitrina.orgs.helpers import get_or_create_parent_org
from vitrina.orgs.models import Organization
from vitrina.admin import RevisionCommentVersionAdmin


class RootCategoryFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("kategoriją")

    parameter_name = "root"

    def lookups(self, request, model_admin):
        for cat in Category.objects.filter(depth=1):
            yield (cat.id, cat.title)

    def queryset(self, request, queryset):
        cat_id = self.value()
        if cat_id:
            cat = Category.objects.get(id=cat_id)
            return queryset.filter(path__startswith=cat.path)


class DatasetGroupCategoryUriInline(admin.TabularInline):
    model = DatasetGroupCategoryUri
    extra = 0
    fields = ("group", "uri")
    verbose_name = _("Kategorijos URI specifinei parinktai grupei")
    verbose_name_plural = _("Kategorijos URI specifinei parinktai grupei")


class CategoryAdmin(TreeAdmin, RevisionCommentVersionAdmin):
    form = movenodeform_factory(Category)
    list_display = [
        "title",
        "numchild",
    ]
    list_filter = [
        RootCategoryFilter,
        "datasetgroupcategoryuri__group",
    ]
    search_fields = ("title",)
    inlines = [DatasetGroupCategoryUriInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if change and ("_position" in form.changed_data or "_ref_node_id" in form.changed_data):
            # save related datasets to update search index
            for dataset in obj.dataset_set.all():
                dataset.save()


class LicenceAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "title",
        "is_default",
    )
    fields = (
        "title",
        "description",
        "url",
        "is_default",
    )

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            Licence.objects.filter(is_default=True).update(is_default=False)
        super().save_model(request, obj, form, change)


class FrequencyAdmin(RevisionCommentVersionAdmin):
    list_display = ("title", "is_default", "hours")
    fields = (
        "title",
        "title_en",
        "hours",
        "uri",
        "is_default",
    )

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            Frequency.objects.filter(is_default=True).update(is_default=False)
        super().save_model(request, obj, form, change)


class AreaOfManagementAdmin(RevisionCommentVersionAdmin):
    form = AreaOfManagementAdminForm
    list_display = ("name_lt_verbose", "organization_count")
    fields = ("name_lt", "name_en", "organizations")
    search_fields = ("name_lt", "name_en")

    def get_organizations(self, obj):
        return ", ".join([org.name for org in obj.organization_set.all()])

    get_organizations.short_description = _("organizacijos")

    def organization_count(self, obj):
        return obj.organization_set.count()

    organization_count.short_description = _("Priskirtų organizacijų kiekis")

    def name_lt_verbose(self, obj):
        return obj.name_lt

    name_lt_verbose.short_description = _("Pavadinimas")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        current_orgs = set(obj.organization_set.all())
        new_orgs = set(form.cleaned_data.get("organizations", []))

        orgs_to_remove = current_orgs - new_orgs
        orgs_to_add = new_orgs - current_orgs

        Organization.fix_tree(fix_paths=True)

        if orgs_to_remove:
            unassigned_area = AreaOfManagement.objects.get(pk=1)  # Unassigned
            unassigned_parent = Organization.objects.get(title="Nepriskirta")

            for org in orgs_to_remove:
                org.jurisdiction = unassigned_area
                org.save()
                # Update hierarchy tree
                org.move(unassigned_parent, "sorted-child")
                org.refresh_from_db()

        if orgs_to_add:
            for org in orgs_to_add:
                org.jurisdiction = obj
                org.save()
                # Update hierarchy tree
                if org.jurisdiction_id != 1:
                    parent_org = get_or_create_parent_org(obj)
                    org.move(parent_org, "sorted-child")
                    org.refresh_from_db()

        # Update organization name if area of management name is changed
        if (
            "name_lt" in form.changed_data
            and "name_lt" in form.initial
            and Organization.objects.filter(title=form.initial["name_lt"]).exists()
        ):
            org = Organization.objects.get(title=form.initial["name_lt"])
            org.title = obj.name_lt
            org.save()

    def delete_model(self, request, obj):
        for org in obj.organization_set.all():
            org.jurisdiction = AreaOfManagement.objects.get(pk=1)  # Unassigned
            org.save()
        super().delete_model(request, obj)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("organization_set")

    def history_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = _("Valdymo srities koregavimo istorija")
        return super().history_view(request, object_id, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}

        extra_context.update(
            {
                "title": _("Pridėti valdymo sritį"),
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
            }
        )
        return super().add_view(request, form_url, extra_context)


class GeoportalCategoryAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "title",
        "categories_display",
    )
    autocomplete_fields = ["categories"]

    def categories_display(self, obj):
        return mark_safe("<br/>".join([cat.title for cat in obj.categories.all()]))

    categories_display.short_description = _("Kategorijos")


class GeoportalFrequencyAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "title",
        "frequency",
    )


class StatusAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = ("name", "codename", "is_default", "url")
    fields = ("name", "description", "codename", "url", "is_default")

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            Status.objects.filter(is_default=True).update(is_default=False)
        super().save_model(request, obj, form, change)


@admin.register(ConceptSchema)
class ConceptSchemaAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = ("label", "uri", "description")


@admin.register(Concept)
class ConceptAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = ("code", "uri", "label", "description")
    list_filter = ("concept_schemas",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).prefetch_related("concept_schemas")

    def has_delete_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        if obj and obj.code == "UAPI":
            return False
        return super().has_delete_permission(request, obj)


@admin.register(ApplicableLegislation)
class ApplicableLegislationAdmin(RevisionCommentVersionAdmin):
    list_display = ("description", "url")


admin.site.register(AreaOfManagement, AreaOfManagementAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Licence, LicenceAdmin)
admin.site.register(Frequency, FrequencyAdmin)
admin.site.register(GeoportalCategory, GeoportalCategoryAdmin)
admin.site.register(GeoportalFrequency, GeoportalFrequencyAdmin)
admin.site.register(Status, StatusAdmin)
