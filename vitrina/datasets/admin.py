import csv
import math
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytz
from django.contrib import admin
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet, Q
from django.db.models.functions import Coalesce
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from vitrina import settings
from vitrina.datasets.forms import DatasetAdminForm
from vitrina.datasets.models import (
    Dataset,
    DatasetGroup,
    Attribution,
    Type,
    Relation,
    DatasetReport,
    Contact,
    GeoportalDataServiceTypeValue,
    DCATResourceSubclass,
    DatasetRelation,
)
from vitrina.filters import FormatFilter
from vitrina.helpers import get_current_domain
from vitrina.orgs.models import Representative
from vitrina.resources.models import FormatName
from vitrina.structure.services import get_data_from_spinta, to_row
from vitrina.admin import RevisionCommentVersionAdmin


TagModel = Dataset.tags.tag_model


class AttributionAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "name",
        "title",
    )


class DatasetAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    search_fields = ("translations__title",)
    list_display = ("title", "description", "is_public")
    form = DatasetAdminForm
    readonly_fields = ("uuid",)

    def has_change_permission(self, request, obj=None):
        """Control who can edit datasets"""
        return request.user.has_perm("vitrina_datasets.change_dataset")

    def has_delete_permission(self, request, obj=None):
        """Control who can delete datasets"""
        return request.user.has_perm("vitrina_datasets.delete_dataset")

    def has_add_permission(self, request):
        """Control who can add datasets"""
        return request.user.has_perm("vitrina_datasets.add_dataset")

    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly for view-only users"""
        readonly_fields = list(super().get_readonly_fields(request, obj))

        if request.user.has_perm("vitrina_datasets.view_dataset") and not request.user.has_perm(
            "vitrina_datasets.change_dataset"
        ):
            readonly_fields.extend([field.name for field in self.model._meta.fields])

        return readonly_fields


class GroupAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = ("title",)


class TypeAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = ("title",)


class DCATResourceSubclassAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = ("title", "description")


class RelationAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = ("title",)


class DatasetLateFilter(admin.SimpleListFilter):
    title = _("Vėluoja")

    parameter_name = "late"

    def lookups(self, request, model_admin):
        return [
            ("yes", _("Taip")),
            ("no", _("Ne")),
        ]

    def queryset(self, request, queryset):
        late_ids = []
        not_late_ids = []
        for obj in queryset:
            distribution = (
                obj.datasetdistribution_set.annotate(effective_updated=Coalesce("data_last_updated", "modified"))
                .filter(effective_updated__isnull=False)
                .order_by("-effective_updated")
                .first()
            )
            if distribution:
                if obj.frequency and obj.frequency.hours:
                    need_to_modify = distribution.effective_updated + timedelta(hours=obj.frequency.hours)
                    now = timezone.now()
                    if need_to_modify < now:
                        late_ids.append(obj.id)
            if obj.id not in late_ids:
                not_late_ids.append(obj.id)

        if self.value() == "yes":
            return queryset.filter(pk__in=late_ids)
        if self.value() == "no":
            return queryset.filter(pk__in=not_late_ids)


class DatasetReportAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "root_organization_display",
        "organization_display",
        "title_display",
        "coordinators_display",
        "managers_display",
        "vda_display",
        "distribution_published_display",
        "frequency_display",
        "spinta_modified_display",
        "distribution_modified_display",
        "late_display",
    )
    list_display_links = None
    search_fields = (
        "translations__title",
        "organization__title",
        "creator_text",
        "representative_emails",
        "vda_representative_emails",
    )
    list_filter = (
        FormatFilter,
        DatasetLateFilter,
        "organization",
    )
    change_list_template = "vitrina/datasets/admin/dataset_report_change_list.html"

    def has_module_permission(self, request):
        return request.user.has_perm("vitrina_datasets.view_datasetreport")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.filter(
            deleted__isnull=True,
            deleted_on__isnull=True,
            organization_id__isnull=False,
            translations__title__isnull=False,
            status=Dataset.HAS_DATA,
        ).distinct()
        queryset = queryset.annotate(representative_emails=ArrayAgg("representatives__email"))
        queryset = queryset.annotate(
            vda_representative_emails=ArrayAgg(
                "organization__representatives__email",
                filter=Q(
                    Q(tags__name__iexact="vda") & Q(organization__representatives__email__icontains="@stat.gov.lt")
                ),
                distinct=True,
            )
        )
        return queryset

    def organization_display(self, obj):
        if obj.organization:
            if len(obj.organization.title) >= 40:
                title = obj.organization.title[:40] + "..."
            else:
                title = obj.organization.title
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.organization.get_absolute_url(),
                title,
            )
        elif obj.creator_text:
            if len(obj.creator_text) >= 40:
                return obj.creator_text[:40] + "..."
            else:
                return obj.creator_text
        return "-"

    organization_display.short_description = _("Institucija")
    organization_display.allow_tags = True

    def root_organization_display(self, obj):
        if obj.organization:
            root_organization = obj.organization.get_root()
            if root_organization:
                if len(root_organization.title) >= 40:
                    title = root_organization.title[:40] + "..."
                else:
                    title = root_organization.title
                return format_html(
                    '<a href="{}" target="_blank">{}</a>',
                    root_organization.get_absolute_url(),
                    title,
                )
        return "-"

    root_organization_display.short_description = _("Tėvinė institucija")
    root_organization_display.allow_tags = True

    def title_display(self, obj):
        if len(obj.title) >= 40:
            title = obj.title[:40] + "..."
        else:
            title = obj.title
        return format_html('<a href="{}" target="_blank">{}</a>', obj.get_absolute_url(), title)

    title_display.short_description = _("Duomenų rinkinys")
    title_display.allow_tags = True

    def coordinators_display(self, obj: Dataset) -> SafeString | str:
        coordinators = obj.representatives.filter(role__in=Representative.COORDINATOR_ROLES).values_list(
            "email", flat=True
        )
        if coordinators:
            return mark_safe("<br/>".join(coordinators))
        return "-"

    coordinators_display.short_description = _("Koordinatoriai")
    coordinators_display.allow_tags = True

    def managers_display(self, obj: Dataset) -> SafeString | str:
        managers = obj.representatives.filter(role__in=Representative.MANAGER_ROLES).values_list("email", flat=True)
        if managers:
            return mark_safe("<br/>".join(managers))
        return "-"

    managers_display.short_description = _("Tvarkytojai")
    managers_display.allow_tags = True

    def vda_display(self, obj):
        if obj.tags.filter(name__iexact="vda").exists() and obj.organization:
            representatives = obj.organization.representatives.filter(email__icontains="@stat.gov.lt").values_list(
                "email", flat=True
            )
            if representatives:
                return mark_safe("<br/>".join(representatives))
        return "-"

    vda_display.short_description = _("VDA tvarkytojai")
    vda_display.allow_tags = True

    def distribution_published_display(self, obj):
        if distribution := obj.datasetdistribution_set.order_by("created").first():
            tz = pytz.timezone(settings.TIME_ZONE)
            return distribution.created.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"

    distribution_published_display.short_description = mark_safe(
        _("Duomenų šaltinio pirmo</br>publikavimo data saugykloje")
    )

    def frequency_display(self, obj):
        if obj.frequency:
            return obj.frequency.title
        return "-"

    frequency_display.short_description = mark_safe(_("Duomenų atnaujinimo</br>periodiškumas"))

    def spinta_modified_display(self, obj):
        if distribution := obj.datasetdistribution_set.filter(modified__isnull=False).order_by("-modified").first():
            if (
                distribution.format
                and distribution.format.extension in (FormatName.API, FormatName.UAPI)
                and distribution.download_url
            ):
                modified = None
                is_model_url = False
                download_url = urlparse(distribution.download_url)
                path_parts = [p for p in download_url.path.split("/") if p]

                if path_parts and path_parts[-1] != ":ns" and path_parts[-1][0].isupper():
                    is_model_url = True

                if is_model_url:
                    latest_change = get_data_from_spinta(download_url.path, ":changes/-1/", timeout=10)
                    latest_change = latest_change.get("_data")
                    modified = latest_change[0].get("_created") if latest_change else None
                else:
                    models = get_data_from_spinta(download_url.path)
                    models = models.get("_data", [])

                    for model in models:
                        if model_name := model.get("name"):
                            latest_change = get_data_from_spinta(model_name, ":changes/-1/", timeout=10)
                            latest_change = latest_change.get("_data")
                            latest_change_date = latest_change[0].get("_created") if latest_change else None

                            if latest_change_date:
                                if not modified:
                                    modified = latest_change_date
                                elif latest_change_date > modified:
                                    modified = latest_change_date

                if modified:
                    modified = datetime.fromisoformat(modified)
                    return modified.strftime("%Y-%m-%d %H:%M")
        return "-"

    spinta_modified_display.short_description = mark_safe(_("Duomenys atnaujinti</br>saugykloje"))

    def distribution_modified_display(self, obj):
        distribution = (
            obj.datasetdistribution_set.annotate(effective_updated=Coalesce("data_last_updated", "modified"))
            .filter(effective_updated__isnull=False)
            .order_by("-effective_updated")
            .first()
        )
        if distribution:
            tz = pytz.timezone(settings.TIME_ZONE)
            return distribution.effective_updated.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"

    distribution_modified_display.short_description = mark_safe(_("Metaduomenys atnaujinti</br>kataloge"))

    def _is_late_for(self, obj):
        text = ""
        distribution = (
            obj.datasetdistribution_set.annotate(effective_updated=Coalesce("data_last_updated", "modified"))
            .filter(effective_updated__isnull=False)
            .order_by("-effective_updated")
            .first()
        )
        if distribution:
            if obj.frequency and obj.frequency.hours:
                need_to_modify = distribution.effective_updated + timedelta(hours=obj.frequency.hours)
                now = timezone.now()
                if need_to_modify < now:
                    late_for = now - need_to_modify
                    if late_for.days > 0:
                        if late_for == 1:
                            text = _(f"Vėluoja {late_for.days} dieną")
                        else:
                            text = _(f"Vėluoja {late_for.days} dienas")
                    else:
                        hours = math.ceil(late_for.seconds / 3600)
                        if hours == 1:
                            text = _(f"Vėluoja {hours} valandą")
                        else:
                            text = _(f"Vėluoja {hours} valandas")
        return text

    def _is_late_for_days(self, obj):
        distribution = (
            obj.datasetdistribution_set.annotate(effective_updated=Coalesce("data_last_updated", "modified"))
            .filter(effective_updated__isnull=False)
            .order_by("-effective_updated")
            .first()
        )
        if distribution:
            if obj.frequency and obj.frequency.hours:
                need_to_modify = distribution.effective_updated + timedelta(hours=obj.frequency.hours)
                now = timezone.now()
                if need_to_modify < now:
                    late_for = now - need_to_modify
                    return late_for.days
        return 0

    def late_display(self, obj):
        late_for = self._is_late_for(obj)
        if late_for:
            return format_html('<span style="color: red;">{}</span>', late_for)
        return "-"

    late_display.short_description = _("Vėluoja")
    late_display.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        result = super().changelist_view(request, extra_context)
        if request.GET.get("format") and request.GET.get("format") == "csv":
            if change_list := result.context_data.get("cl"):
                stream = self._export_dataset_report(change_list.queryset, request)
                result = StreamingHttpResponse(stream, content_type="text/csv")
                result["Content-Disposition"] = "attachment; filename=Ataskaita.csv"
                result["Cache-Control"] = "no-cache"
                result["X-Accel-Buffering"] = "no"
        return result

    def _export_dataset_report(self, queryset, request):
        class _Stream(object):
            def write(self, value):
                return value

        cols = {
            "root_organization": _("Tėvinė institucija"),
            "organization": _("Institucija"),
            "dataset_title": _("Duomenų rinkinio pavadinimas"),
            "coordinators": _("Koodinatoriai"),
            "managers": _("Tvarkytojai"),
            "vda_representatives": _("VDA tvarkytojai"),
            "dataset_url": _("Duomenų rinkinio nuoroda"),
            "created": _("Duomenų šaltinio pirmo publikavimo data saugykloje"),
            "frequency": _("Duomenų atnaujinimo periodiškumas"),
            "spinta_modified": _("Duomenys atnaujinti saugykloje"),
            "modified": _("Metaduomenys atnaujinti kataloge"),
            "late": _("Vėlavimas, dienomis"),
        }
        rows = self._get_dataset_report(cols, queryset, request)
        rows = ({v: row[k] for k, v in cols.items()} for row in rows)

        stream = _Stream()
        yield stream.write(b"\xef\xbb\xbf")

        writer = csv.DictWriter(stream, fieldnames=cols.values(), delimiter=";")
        yield writer.writeheader()
        for row in rows:
            yield writer.writerow(row)

    def _get_dataset_report(self, cols, queryset, request):
        for item in queryset:
            coordinators = item.representatives.filter(role__in=Representative.COORDINATOR_ROLES).values_list(
                "email", flat=True
            )
            if coordinators:
                coordinators = "\n".join(coordinators)
            else:
                coordinators = "-"

            managers = item.representatives.filter(role__in=Representative.MANAGER_ROLES).values_list(
                "email", flat=True
            )
            if managers:
                managers = "\n".join(managers)
            else:
                managers = "-"

            vda_representatives = "-"
            if item.tags.filter(name__iexact="vda").exists() and item.organization:
                representatives = item.organization.representatives.filter(email__icontains="@stat.gov.lt").values_list(
                    "email", flat=True
                )
                if representatives:
                    vda_representatives = "\n".join(representatives)

            organization = "-"
            root_organization = "-"
            if item.organization:
                organization = item.organization.title
                if root := item.organization.get_root():
                    root_organization = root.title
            elif item.creator_text:
                organization = item.creator_text

            yield to_row(
                cols.keys(),
                {
                    "organization": organization,
                    "root_organization": root_organization,
                    "dataset_title": item.title,
                    "coordinators": coordinators,
                    "managers": managers,
                    "vda_representatives": vda_representatives,
                    "dataset_url": "%s%s" % (get_current_domain(request), item.get_absolute_url()),
                    "created": self.distribution_published_display(item),
                    "frequency": self.frequency_display(item),
                    "spinta_modified": self.spinta_modified_display(item),
                    "modified": self.distribution_modified_display(item),
                    "late": self._is_late_for_days(item),
                },
            )


class ContactAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "email",
        "phone_display",
        "content_type_display",
        "content_object_display",
    )
    search_fields = ("email", "phone", "content_object")
    title = _("Kontaktai")

    def phone_display(self, obj):
        return obj.phone

    phone_display.short_description = _("Telefono numeris")

    def content_type_display(self, obj):
        return obj.content_type

    content_type_display.short_description = _("Kontaktinio objekto tipas")

    def content_object_display(self, obj):
        return obj.content_object

    content_object_display.short_description = _("Kontaktinis objektas")


class GeoportalDataServiceTypeValueInline(admin.TabularInline):
    model = GeoportalDataServiceTypeValue
    extra = 0


class DatasetRelationAdmin(RevisionCommentVersionAdmin):
    list_display = ("dataset", "relation", "part_of")
    search_fields = ("dataset", "relation", "part_of")
    list_filter = ("relation",)

    def get_queryset(self, request) -> QuerySet[DatasetRelation]:
        return super().get_queryset(request).select_related("dataset", "relation", "part_of")


@admin.register(TagModel)
class DatasetTagAdmin(RevisionCommentVersionAdmin):
    list_display = ("name", "count")
    search_fields = ("name",)

    def has_add_permission(self, request):
        return request.user.has_perm("vitrina_datasets.add_tagulous_dataset_tags")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("vitrina_datasets.change_tagulous_dataset_tags")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("vitrina_datasets.delete_tagulous_dataset_tags")

    def get_actions(self, request):
        actions = super().get_actions(request)

        # Remove merge action for view-only users
        if not request.user.has_perm("vitrina_datasets.change_tagulous_dataset_tags"):
            actions.pop("merge_tags", None)

        return actions

    def get_readonly_fields(self, request, obj=None):
        if not request.user.has_perm("vitrina_datasets.change_tagulous_dataset_tags"):
            return [field.name for field in self.model._meta.fields]
        return []


admin.site.register(Dataset, DatasetAdmin)
admin.site.register(DatasetRelation, DatasetRelationAdmin)
admin.site.register(Attribution, AttributionAdmin)
admin.site.register(DatasetGroup, GroupAdmin)
admin.site.register(Type, TypeAdmin)
admin.site.register(DCATResourceSubclass, DCATResourceSubclassAdmin)
admin.site.register(Relation, RelationAdmin)
admin.site.register(DatasetReport, DatasetReportAdmin)
admin.site.register(Contact, ContactAdmin)
