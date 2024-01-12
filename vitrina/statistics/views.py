import json
from datetime import datetime

import pandas as pd
from django.views.generic import ListView
from django.template.defaultfilters import date as _date
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.services import get_frequency_and_format, update_facet_data, get_query_for_frequency, \
    get_values_for_frequency
from vitrina.helpers import get_stats_filter_options_based_on_model
from vitrina.statistics.models import StatRoute


class StatRouteListView(ListView):
    template_name = 'vitrina/statistics/list.html'
    model = StatRoute
    paginate_by = 20
    ordering = ('order',)


class StatsMixin:
    template_name = 'vitrina/statistics/stats.html'
    paginate_by = 0

    model = None
    title = ""
    current_title = ""
    tabs_template_name = None
    filters_template_name = None
    parameter_select_template_name = None
    filter = None
    filter_model = None
    filter_choices = None
    use_str = False
    list_url = ""
    max_values_in_time_chart = 10
    has_time_graph = True

    default_indicator = None
    default_sort = 'sort-desc'
    default_duration = 'duration-yearly'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = self.update_context_data(context)
        context['parent_links'] = self.get_parent_links()
        return context

    def update_context_data(self, context):
        facet_fields = context.get('facets').get('fields')
        filter_data = self.get_filter_data(facet_fields)
        queryset = context['object_list']

        start_date = self.get_start_date()
        indicator = self.request.GET.get('indicator', None) or self.default_indicator
        sorting = self.request.GET.get('sort', None) or self.default_sort
        duration = self.request.GET.get('duration', None) or self.default_duration
        context['options'] = get_stats_filter_options_based_on_model(
            self.model,
            duration,
            sorting,
            indicator,
            filter=self.filter
        )

        frequency, ff = get_frequency_and_format(duration)
        labels = self.get_time_labels(start_date, frequency)
        date_field = self.get_date_field()
        values = get_values_for_frequency(frequency, date_field)

        bar_chart_data = []
        time_chart_data = []

        for item in filter_data:
            count = 0
            data = []

            query = {self.filter: item['filter_value']}
            filter_queryset_ids = queryset.filter(**query).values_list('pk', flat=True)
            filter_queryset = self.get_index_queryset().filter(pk__in=filter_queryset_ids)

            count_data = self.get_data_for_indicator(indicator, values, filter_queryset)

            for label in labels:
                label_query = get_query_for_frequency(frequency, date_field, label)
                label_count_data = count_data.filter(**label_query)
                count = self.get_count(label, indicator, frequency, label_count_data, count)

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            display_value = self.get_display_value(item)
            dt = {
                'label': display_value,
                'data': data,
                'borderWidth': 1,
                'fill': True,
            }
            time_chart_data.append(dt)

            item['count'] = self.get_item_count(data, indicator)
            item['display_value'] = display_value
            item = self.update_item_data(item)
            bar_chart_data.append(item)

        if sorting == 'sort-desc':
            time_chart_data = sorted(time_chart_data, key=lambda x: x['data'][-1]['y'], reverse=True)
            bar_chart_data = sorted(bar_chart_data, key=lambda x: x['count'], reverse=True)
        else:
            time_chart_data = sorted(time_chart_data, key=lambda x: x['data'][-1]['y'])
            bar_chart_data = sorted(bar_chart_data, key=lambda x: x['count'])

        max_count = max([x['count'] for x in bar_chart_data]) if bar_chart_data else 0

        context['title'] = self.title
        context['current_title'] = self.current_title
        context['tabs_template_name'] = self.tabs_template_name
        context['filters_template_name'] = self.filters_template_name
        context['parameter_select_template_name'] = self.parameter_select_template_name
        context['list_url'] = self.list_url
        context['has_time_graph'] = self.has_time_graph

        context['active_filter'] = self.filter
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['duration'] = duration

        context['graph_title'] = self.get_graph_title(indicator)
        context['xAxis_title'] = self.get_time_axis_title(indicator)
        context['yAxis_title'] = self.get_title_for_indicator(indicator)
        context['time_chart_data'] = json.dumps(time_chart_data[:self.max_values_in_time_chart])

        context['bar_chart_data'] = bar_chart_data
        context['max_count'] = max_count

        return context

    def get_filter_data(self, facet_fields):
        return update_facet_data(
            self.request,
            facet_fields,
            self.filter,
            self.filter_model,
            self.filter_choices,
            self.use_str
        )

    def get_start_date(self):
        if obj := self.model.objects.order_by('created').first():
            return obj.created
        return datetime.now()

    def get_time_labels(self, start_date, frequency):
        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()
        return labels

    def get_index_queryset(self):
        return self.model.objects.all()

    def get_data_for_indicator(self, indicator, values, filter_queryset):
        return []

    def get_count(self, label, indicator, frequency, data, count):
        return 0

    def get_title_for_indicator(self, indicator):
        return indicator

    def get_graph_title(self, indicator):
        return ""

    def get_display_value(self, item):
        return item.get('display_value')

    def update_item_data(self, item):
        return item

    def get_parent_links(self):
        return {}

    def get_date_field(self):
        return 'created'

    def get_time_axis_title(self, indicator):
        return _('Laikas')

    def get_item_count(self, data, indicator):
        if data:
            return data[-1]['y']
        return 0
