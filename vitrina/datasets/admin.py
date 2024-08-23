import csv
import math
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytz
from django.contrib import admin
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from parler.admin import TranslatableAdmin
from reversion.admin import VersionAdmin

import tagulous
from django.utils.translation import gettext_lazy as _

from vitrina import settings
from vitrina.datasets.models import Dataset, DatasetGroup, Attribution, DataServiceType, DataServiceSpecType, Type, \
    Relation, DatasetReport
from vitrina.helpers import get_current_domain
from vitrina.resources.models import FormatName
from vitrina.structure.services import get_data_from_spinta, to_row


class AttributionAdmin(admin.ModelAdmin):
    list_display = ('name', 'title',)


class DatasetAdmin(TranslatableAdmin, VersionAdmin):
    list_display = ('title', 'description', 'is_public')


class GroupAdmin(TranslatableAdmin):
    list_display = ('title',)


class DataServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('title',)


class DataServiceSpecTypeAdmin(admin.ModelAdmin):
    list_display = ('title',)


class TypeAdmin(TranslatableAdmin):
    list_display = ('title',)


class RelationAdmin(TranslatableAdmin):
    list_display = ('title',)


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
            if distribution := obj.datasetdistribution_set.filter(modified__isnull=False).order_by('-modified').first():
                if obj.frequency and obj.frequency.hours:
                    need_to_modify = distribution.modified + timedelta(hours=obj.frequency.hours)
                    now = timezone.now()
                    if need_to_modify < now:
                        late_ids.append(obj.id)
            if obj.id not in late_ids:
                not_late_ids.append(obj.id)

        if self.value() == "yes":
            return queryset.filter(pk__in=late_ids)
        if self.value() == "no":
            return queryset.filter(pk__in=not_late_ids)


# This is needed to allow "format" query argument in DatasetReport list
class FormatFilter(admin.SimpleListFilter):
    title = ''
    parameter_name = 'format'
    template = 'vitrina/datasets/admin/hidden_filter.html'

    def lookups(self, request, model_admin):
        return (request.GET.get(self.parameter_name), ''),

    def queryset(self, request, queryset):
        return queryset


class DatasetReportAdmin(admin.ModelAdmin):
    list_display = (
        'organization_display',
        'title_display',
        'distribution_published_display',
        'frequency_display',
        'spinta_modified_display',
        'distribution_modified_display',
        'late_display'
    )
    list_display_links = None
    search_fields = ('translations__title', 'organization__title',)
    list_filter = (FormatFilter, DatasetLateFilter, 'organization',)
    change_list_template = 'vitrina/datasets/admin/dataset_report_change_list.html'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def organization_display(self, obj):
        if len(obj.organization.title) >= 40:
            title = obj.organization.title[:40] + "..."
        else:
            title = obj.organization.title
        return format_html('<a href="{}" target="_blank">{}</a>', obj.organization.get_absolute_url(), title)
    organization_display.short_description = _('Institucija')
    organization_display.allow_tags = True

    def title_display(self, obj):
        if len(obj.title) >= 40:
            title = obj.title[:40] + "..."
        else:
            title = obj.title
        return format_html('<a href="{}" target="_blank">{}</a>', obj.get_absolute_url(), title)
    title_display.short_description = _('Duomenų rinkinys')
    title_display.allow_tags = True

    def distribution_published_display(self, obj):
        if distribution := obj.datasetdistribution_set.order_by('created').first():
            tz = pytz.timezone(settings.TIME_ZONE)
            return distribution.created.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"
    distribution_published_display.short_description = mark_safe(
        _('Duomenų šaltinio pirmo</br>publikavimo data saugykloje')
    )

    def frequency_display(self, obj):
        if obj.frequency:
            return obj.frequency.title
        return '-'
    frequency_display.short_description = mark_safe(_('Duomenų atnaujinimo</br>periodiškumas'))

    def spinta_modified_display(self, obj):
        if distribution := obj.datasetdistribution_set.filter(modified__isnull=False).order_by('-modified').first():
            if (
                distribution.format and
                distribution.format.extension in (FormatName.API, FormatName.UAPI) and
                distribution.download_url
            ):
                modified = None
                is_model_url = False
                download_url = urlparse(distribution.download_url)
                path_parts = [p for p in download_url.path.split('/') if p]

                if (
                    path_parts and
                    path_parts[-1] != ':ns' and
                    path_parts[-1][0].isupper()
                ):
                    is_model_url = True

                if is_model_url:
                    latest_change = get_data_from_spinta(download_url.path, ':changes/-1/', timeout=10)
                    latest_change = latest_change.get('_data')
                    modified = latest_change[0].get('_created') if latest_change else None
                else:
                    models = get_data_from_spinta(download_url.path)
                    models = models.get('_data', [])

                    for model in models:
                        if model_name := model.get('name'):
                            latest_change = get_data_from_spinta(model_name, ':changes/-1/', timeout=10)
                            latest_change = latest_change.get('_data')
                            latest_change_date = latest_change[0].get('_created') if latest_change else None

                            if latest_change_date:
                                if not modified:
                                    modified = latest_change_date
                                elif latest_change_date > modified:
                                    modified = latest_change_date

                if modified:
                    modified = datetime.fromisoformat(modified)
                    return modified.strftime("%Y-%m-%d %H:%M")
        return "-"
    spinta_modified_display.short_description = mark_safe(_('Duomenys atnaujinti</br>saugykloje'))

    def distribution_modified_display(self, obj):
        if distribution := obj.datasetdistribution_set.filter(modified__isnull=False).order_by('-modified').first():
            tz = pytz.timezone(settings.TIME_ZONE)
            return distribution.modified.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        return "-"
    distribution_modified_display.short_description = mark_safe(_('Metaduomenys atnaujinti</br>kataloge'))

    def _is_late_for(self, obj):
        text = ""
        if distribution := obj.datasetdistribution_set.filter(modified__isnull=False).order_by('-modified').first():
            if obj.frequency and obj.frequency.hours:
                need_to_modify = distribution.modified + timedelta(hours=obj.frequency.hours)
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

    def late_display(self, obj):
        late_for = self._is_late_for(obj)
        if late_for:
            return format_html('<span style="color: red;">{}</span>', late_for)
        return "-"
    late_display.short_description = _('Vėluoja')
    late_display.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        result = super().changelist_view(request, extra_context)
        if request.GET.get('format') and request.GET.get('format') == 'csv':
            if change_list := result.context_data.get('cl'):
                stream = self._export_dataset_report(change_list.queryset, request)
                result = StreamingHttpResponse(stream, content_type='text/csv')
                result['Content-Disposition'] = 'attachment; filename=Ataskaita.csv'
        return result

    def _export_dataset_report(self, queryset, request):
        class _Stream(object):
            def write(self, value):
                return value

        cols = {
            'organization': _("Institucija"),
            'dataset_title': _("Duomenų rinkinio pavadinimas"),
            'dataset_url': _("Duomenų rinkinio nuoroda"),
            'created': _("Duomenų šaltinio pirmo publikavimo data saugykloje"),
            'frequency': _("Duomenų atnaujinimo periodiškumas"),
            'spinta_modified': _("Duomenys atnaujinti saugykloje"),
            'modified': _("Metaduomenys atnaujinti kataloge"),
            'late': _("Vėluoja"),
        }
        rows = self._get_dataset_report(cols, queryset, request)
        rows = ({v: row[k] for k, v in cols.items()} for row in rows)

        stream = _Stream()
        yield stream.write(b'\xef\xbb\xbf')

        writer = csv.DictWriter(stream, fieldnames=cols.values(), delimiter=';')
        yield writer.writeheader()
        for row in rows:
            yield writer.writerow(row)

    def _get_dataset_report(self, cols, queryset, request):
        for item in queryset:
            yield to_row(cols.keys(), {
                'organization': item.organization.title,
                'dataset_title': item.title,
                'dataset_url': "%s%s" % (get_current_domain(request), item.get_absolute_url()),
                'created': self.distribution_published_display(item),
                'frequency': self.frequency_display(item),
                'spinta_modified': self.spinta_modified_display(item),
                'modified': self.distribution_modified_display(item),
                'late': self._is_late_for(item) or "-",
            })


admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Attribution, AttributionAdmin)
admin.site.register(DatasetGroup, GroupAdmin)
admin.site.register(DataServiceType, DataServiceTypeAdmin)
admin.site.register(DataServiceSpecType, DataServiceSpecTypeAdmin)
admin.site.register(Type, TypeAdmin)
admin.site.register(Relation, RelationAdmin)
admin.site.register(DatasetReport, DatasetReportAdmin)

tagulous.admin.register(Dataset.tags)
