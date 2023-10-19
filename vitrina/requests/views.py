import json
from typing import List

import pytz
from django.views.generic import CreateView, UpdateView, DetailView
from collections import OrderedDict

import numpy as np
import pandas as pd
from datetime import date, datetime
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.db.models import Case, When
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, DeleteView
from reversion.models import Version
from haystack.generic_views import FacetedSearchView

from vitrina.comments.models import Comment
from vitrina.datasets.services import get_query_for_frequency, get_frequency_and_format, get_values_for_frequency, \
    sort_publication_stats, get_total_by_indicator_from_stats
from vitrina.settings import ELASTIC_FACET_SIZE
from vitrina.datasets.forms import PlanForm
from vitrina.orgs.services import has_perm, Action
from vitrina.orgs.models import Representative
from vitrina.helpers import get_selected_value
from vitrina.helpers import Filter
from vitrina.helpers import DateFilter
from reversion import set_comment
from vitrina.requests.services import update_facet_data
from django.db.models import QuerySet, Count, Max, Q, Avg, Sum, Case, When, IntegerField
from reversion.views import RevisionMixin
from vitrina.datasets.models import Dataset, DatasetGroup
from vitrina.requests.models import Request, Organization, RequestStructure, RequestObject, RequestAssignment
from django.template.defaultfilters import date as _date

from vitrina.plans.models import Plan, PlanRequest
from vitrina.requests.forms import RequestForm, RequestEditOrgForm, RequestPlanForm, RequestSearchForm

from django.utils.translation import gettext_lazy as _

from vitrina.statistics.views import StatsMixin
from vitrina.tasks.models import Task
from vitrina.views import HistoryView, HistoryMixin, PlanMixin
from django.contrib import messages


class RequestListView(FacetedSearchView):
    template_name = 'vitrina/requests/list.html'
    facet_fields = [
        'status',
        'dataset_status',
        'organization',
        'jurisdiction',
        'category',
        'parent_category',
        'groups', 'tags',
        'created'
    ]
    max_num_facets = 20
    paginate_by = 20
    form_class = RequestSearchForm
    date_facet_fields = [
        {
            'field': 'created',
            'start_date': date(2019, 1, 1),
            'end_date': date.today(),
            'gap_by': 'month',
        },
    ]

    def get_queryset(self):
        requests = super().get_queryset()
        sorting = self.request.GET.get('sort', None)
        options = {"size": ELASTIC_FACET_SIZE}
        for field in self.facet_fields:
            requests = requests.facet(field, **options)
        if sorting is None or sorting == 'sort-by-date-newest':
            requests = requests.order_by('-type_order', '-created')
        elif sorting == 'sort-by-date-oldest':
            requests = requests.order_by('-type_order', 'created')
        elif sorting == 'sort-by-title':
            if self.request.LANGUAGE_CODE == 'lt':
                requests = requests.order_by('-type_order', 'lt_title_s')
            else:
                requests = requests.order_by('-type_order', 'en_title_s')
        return requests

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get('facets').get('fields')
        date_facets = context['facets']['dates']
        form = context.get('form')
        filter_args = (self.request, form, facet_fields)
        sorting = self.request.GET.get('sort', None)
        extra_context = {
            'filters': [
                Filter(
                    *filter_args,
                    'status',
                    _("Poreikio būsena"),
                    choices=Request.FILTER_STATUSES,
                    multiple=False,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    'dataset_status',
                    _("Duomenų rinkinio būsena"),
                    choices=Dataset.FILTER_STATUSES,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    'organization',
                    _("Organizacija"),
                    Organization,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    'jurisdiction',
                    _("Valdymo sritis"),
                    Organization,
                    multiple=True,
                    is_int=False,
                ),
                DateFilter(
                    self.request,
                    form,
                    date_facets,
                    'created',
                    _("Pateikimo data"),
                    multiple=False,
                    is_int=False,
                ),
            ],
            'group_facet': update_facet_data(self.request, facet_fields, 'groups', DatasetGroup),
            'selected_groups': get_selected_value(form, 'groups', True, False),
            'q': form.cleaned_data.get('q', ''),
        }
        context.update(extra_context)
        context['sort'] = sorting
        return context


Y_TITLES = {
    'download-request-count': _('Atsisiuntimų (užklausų) skaičius'),
    'download-object-count': _('Atsisiuntimų (objektų) skaičius'),
    'object-count': _('Objektų skaičius'),
    'field-count': _('Savybių (duomenų laukų) skaičius'),
    'model-count': _('Esybių (modelių) skaičius'),
    'distribution-count': _('Duomenų šaltinių (distribucijų) skaičius'),
    'dataset-count': _('Duomenų rinkinių skaičius'),
    'request-count': _('Poreikių skaičius'),
    'request-count-open': _('Poreikių skaičius (neatsakytų)'),
    'request-count-late': _('Poreikių skaičius (vėluojančių)'),
    'project-count': _('Projektų skaičius')
}


class RequestStatsMixin(StatsMixin):
    model = Request
    filters_template_name = 'vitrina/requests/filters.html'
    parameter_select_template_name = 'vitrina/requests/stats_parameter_select.html'
    default_indicator = 'request-count'
    list_url = reverse_lazy('request-list')

    def get_data_for_indicator(self, indicator, values, filter_queryset):
        if indicator == 'request-count':
            data = filter_queryset.values(*values).annotate(count=Count('pk'))
        elif indicator == 'request-count-open':
            data = filter_queryset.filter(status=Request.CREATED).values(*values).annotate(count=Count('pk'))
        else:
            data = (PlanRequest.objects.filter(request_id__in=filter_queryset, plan__deadline__lt=datetime.now())
                    .values(*values).annotate(count=Count('request')))
        return data

    def get_count(self, label, indicator, frequency, data, count):
        if data:
            if indicator == 'object-count' or indicator == 'level-average':
                count = data[0].get('count') or 0
            else:
                count += data[0].get('count') or 0
        return count

    def get_item_count(self, data, indicator):
        count = super().get_item_count(data, indicator)
        if indicator == 'object-count':
            count = sum([x['y'] for x in data])
        return count

    def get_title_for_indicator(self, indicator):
        return Y_TITLES.get(indicator) or indicator

    def get_parent_links(self):
        return {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
        }

    def get_time_axis_title(self, indicator):
        if indicator == 'level-average' or indicator == 'object-count':
            return _("Poreikio pateikimo data")
        else:
            return _("Laikas")


class RequestStatusStatsView(RequestStatsMixin, RequestListView):
    title = _("Būsena")
    current_title = _("Poreikio būsena")
    filter = 'status'
    filter_choices = Request.FILTER_STATUSES

    def get_graph_title(self, indicator):
        return _(f'{self.get_title_for_indicator(indicator)} pagal poreikio būseną laike')

    def update_context_data(self, context):
        facet_fields = context.get('facets').get('fields')
        statuses = self.get_filter_data(facet_fields)
        requests = context['object_list']

        indicator = self.request.GET.get('indicator', None) or 'request-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = self.get_start_date()

        time_chart_data = []
        bar_chart_data = []

        frequency, ff = get_frequency_and_format(duration)
        labels = self.get_time_labels(start_date, frequency)
        date_field = self.get_date_field()
        values = get_values_for_frequency(frequency, date_field)

        for status in statuses:
            count = 0
            data = []
            status_request_ids = requests.filter(status=status['filter_value']).values_list('pk', flat=True)
            status_requests = Request.objects.filter(pk__in=status_request_ids)

            count_data = self.get_data_for_indicator(indicator, values, status_requests)

            for label in labels:
                label_query = get_query_for_frequency(frequency, date_field, label)
                if (
                    indicator == 'request-count'
                ):
                    label_count_data = count_data.filter(**label_query)
                    count = self.get_count(label, indicator, frequency, label_count_data, count)
                elif (
                    indicator == 'request-count-open'
                ):
                    label_count_data = count_data.filter(**label_query)
                    count = self.get_count(label, indicator, frequency, label_count_data, count)
                else:
                    label_count_data = count_data.filter(**label_query)
                    count = self.get_count(label, indicator, frequency, label_count_data, count)

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            dt = {
                'label': str(status['display_value']),
                'data': data,
                'borderWidth': 1,
                'fill': True,
            }
            time_chart_data.append(dt)

            status['count'] = self.get_item_count(data, indicator)
            bar_chart_data.append(status)

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
        context['time_chart_data'] = json.dumps(time_chart_data)

        context['bar_chart_data'] = bar_chart_data
        context['max_count'] = max_count

        return context


class RequestDatasetStatusStatsView(RequestStatsMixin, RequestListView):
    title = _("Duomenų rinkinių būsena")
    current_title = _("Duomenų rinkinių būsenos")
    filter = 'dataset_status'
    filter_choices = Dataset.FILTER_STATUSES
    # filter_model = Dataset

    def get_display_value(self, item):
        st = super().get_display_value(item)
        return str(st)

    def get_graph_title(self, indicator):
        return _(f'{self.get_title_for_indicator(indicator)} pagal duomenų rinkinio būseną laike')


class RequestOrganizationStatsView(RequestStatsMixin, RequestListView):
    title = _("Organizacija")
    current_title = _("Poreikių organizacijos")
    filter = 'organization'
    filter_model = Organization

    def get_graph_title(self, indicator):
        return _(f'{self.get_title_for_indicator(indicator)} pagal organizaciją laike')


class RequestJurisdictionStatsView(RequestStatsMixin, RequestListView):
    title = _("Valdymo sritis")
    current_title = _("Poreikių valdymo sritys")
    filter = 'jurisdiction'
    filter_model = Organization

    def get_graph_title(self, indicator):
        if indicator == 'level-average' or indicator == 'object-count':
            return _(f'{self.get_title_for_indicator(indicator)} '
                     f'pagal rinkinio valdymo sritį rinkinio įkėlimo datai')
        else:
            return _(f'{self.get_title_for_indicator(indicator)} pagal rinkinio valdymo sritį laike')


class RequestPublicationStatsView(RequestStatsMixin, RequestListView):
    title = _("Pateikimo data")
    current_title = _("Poreikių kiekis metuose")
    filter = 'created'

    def get_graph_title(self, indicator):
        return _(f'{self.get_title_for_indicator(indicator)} pagal pateikimo datą')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requests = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'request-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Request.objects.order_by('created').first().created
        max_count = 0
        stats_for_period = {}
        year_stats = {}
        chart_data = []
        bar_chart_data = []

        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        for request in requests:
            created = request.created
            if created is not None:
                year_published = created.year
                year_stats[str(year_published)] = year_stats.get(str(year_published), 0) + 1
                period = str(pd.to_datetime(created).to_period(frequency))
                stats_for_period[period] = stats_for_period.get(period, 0) + 1
        if indicator != 'request-count':
            for yr in year_stats.keys():
                start_date = datetime.strptime(str(yr) + "-1-1", '%Y-%m-%d')
                end_date = datetime.strptime(str(yr) + "-12-31", '%Y-%m-%d')
                tz = pytz.timezone('Europe/Vilnius')
                filtered_requests = requests.filter(created__range=[tz.localize(start_date), tz.localize(end_date)])
                request_ids = []
                for fd in filtered_requests:
                    request_ids.append(fd.pk)
                if indicator == 'request-count-open':
                    total = Request.objects.filter(pk__in=request_ids, status=Request.CREATED).count()
                    year_stats[yr] = total
                else:
                    total = (
                        PlanRequest.objects.filter(request_id__in=request_ids, plan__deadline__lt=datetime.now())
                    ).count()
                    year_stats[yr] = total
        if year_stats:
            keys = list(year_stats.keys())
            values = list(year_stats.values())
            sorted_value_index = np.argsort(values)
            year_stats = sort_publication_stats(sorting, values, keys, year_stats, sorted_value_index)
            max_count = year_stats[max(year_stats, key=lambda key: year_stats[key], default=0)]

        data = []
        total = 0
        for label in labels:
            request_count = stats_for_period.get(str(label), 0)
            if indicator == 'request-count':
                total += request_count
                item = {
                    'display_value': label.year,
                    'count': request_count
                }
                bar_chart_data.append(item)
            elif indicator == 'request-count-open' or indicator == 'request-count-late':
                count = year_stats.get(str(label), 0)
                total += count
                item = {
                    'display_value': label.year,
                    'count': count
                }
                bar_chart_data.append(item)

            if frequency == 'W':
                data.append({'x': _date(label.start_time, ff), 'y': total})
            else:
                data.append({'x': _date(label, ff), 'y': total})

        dt = {
            'label': 'Poreikių kiekis',
            'data': data,
            'borderWidth': 1,
            'fill': True,
        }
        chart_data.append(dt)

        if sorting == 'sort-desc':
            bar_chart_data = sorted(bar_chart_data, key=lambda x: x['count'], reverse=True)
        else:
            bar_chart_data = sorted(bar_chart_data, key=lambda x: x['count'])

        context['title'] = self.title
        context['current_title'] = self.current_title
        context['time_chart_data'] = json.dumps(chart_data)
        context['bar_chart_data'] = bar_chart_data
        context['year_stats'] = year_stats
        context['max_count'] = max_count

        context['graph_title'] = self.get_graph_title(indicator)
        context['yAxis_title'] = self.get_title_for_indicator(indicator)
        context['xAxis_title'] = _('Laikas')

        context['active_filter'] = self.filter
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['duration'] = duration

        context['has_time_graph'] = True
        return context


class RequestYearStatsView(RequestListView):
    template_name = 'vitrina/requests/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        requests = self.get_queryset()
        sorting = self.request.GET.get('sort', None)
        year_stats = {}
        quarter_stats = {}
        selected_year = str(self.kwargs['year'])
        for req in requests:
            created = req.created
            if created is not None:
                year_created = created.year
                year_stats[year_created] = year_stats.get(year_created, 0) + 1
                quarter = str(year_created) + "-Q" + str(pd.Timestamp(created).quarter)
                quarter_stats[quarter] = quarter_stats.get(quarter, 0) + 1
        for key, value in quarter_stats.items():
            if max_count < value:
                max_count = value
        keys = list(quarter_stats.keys())
        values = list(quarter_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting is None or sorting == 'sort-year-desc':
            quarter_stats = OrderedDict(sorted(quarter_stats.items(), reverse=False))
        elif sorting == 'sort-year-asc':
            quarter_stats = OrderedDict(sorted(quarter_stats.items(), reverse=True))
        elif sorting == 'sort-asc':
            quarter_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-desc':
            quarter_stats = {keys[i]: values[i] for i in sorted_value_index}
        context['selected_year'] = selected_year
        context['year_stats'] = quarter_stats
        context['max_count'] = max_count
        context['current_object'] = str('year/' + selected_year)
        context['filter'] = 'publication'
        context['sort'] = sorting
        return context


class RequestQuarterStatsView(RequestListView):
    template_name = 'vitrina/requests/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        requests = self.get_queryset()
        sorting = self.request.GET.get('sort', None)
        monthly_stats = {}
        selected_quarter = str(self.kwargs['quarter'])
        for req in requests:
            created = req.created
            if created is not None:
                year_created = created.year
                if str(year_created) in selected_quarter:
                    quarter = str(year_created) + "-Q" + str(pd.Timestamp(created).quarter)
                    if quarter == selected_quarter:
                        month = str(year_created) + "-" + str('%02d' % created.month)
                        monthly_stats[month] = monthly_stats.get(month, 0) + 1
        for m, mv in monthly_stats.items():
            if max_count < mv:
                max_count = mv
        keys = list(monthly_stats.keys())
        values = list(monthly_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting is None or sorting == 'sort-year-desc':
            monthly_stats = OrderedDict(sorted(monthly_stats.items(), reverse=False))
        elif sorting == 'sort-year-asc':
            monthly_stats = OrderedDict(sorted(monthly_stats.items(), reverse=True))
        elif sorting == 'sort-asc':
            monthly_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-desc':
            monthly_stats = {keys[i]: values[i] for i in sorted_value_index}
        context['selected_quarter'] = self.kwargs['quarter']
        context['year_stats'] = monthly_stats
        context['max_count'] = max_count
        context['current_object'] = str('quarter/' + selected_quarter)
        context['filter'] = 'publication'
        context['sort'] = sorting
        return context


class RequestDetailView(HistoryMixin, PlanMixin, DetailView):
    model = Request
    template_name = 'vitrina/requests/detail.html'
    context_object_name = 'request_object'
    detail_url_name = 'request-detail'
    history_url_name = 'request-history'
    plan_url_name = 'request-plans'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        request: Request = self.object

        extra_context_data = {
            "formats": request.format.replace(" ", "").split(",") if request.format else [],
            "changes": request.changes.replace(" ", "").split(",") if request.changes else [],
            "purposes": request.purpose.replace(" ", "").split(",") if request.purpose else [],
            "structure": RequestStructure.objects.filter(request_id=request.pk),
            # "related_object": request.object,
            "status": request.get_status_display(),
            "user_count": 0,
            'can_update_request': has_perm(
                self.request.user,
                Action.UPDATE,
                request
            ),
            'can_manage_plans': has_perm(
                self.request.user,
                Action.PLAN,
                request
            )
        }
        context_data.update(extra_context_data)
        return context_data


class RequestCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    CreateView
):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Request)

    def form_valid(self, form):
        orgs = form.cleaned_data.get('organizations')
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.status = Request.CREATED
        self.object.save()
        set_comment(Request.CREATED)
        for org in orgs:
            self.object.organizations.add(org)
            requestA = RequestAssignment.objects.create(
                request=self.object,
                organization=org,
                status=self.object.status
            )
            requestA.save()
        self.object.save()
        Task.objects.create(
            title=f"Užregistruotas naujas poreikis: {ContentType.objects.get_for_model(self.object)},"
                  f" id: {self.object.pk}",
            description=f"Portale registruotas naujas poreikis duomenų atvėrimui: "
                        f"{ContentType.objects.get_for_model(self.object)}.",
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.pk,
            status=Task.CREATED
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio registravimas')
        return context_data


class RequestOrgEditView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Request
    form_class = RequestEditOrgForm
    template_name = 'base_form.html'
    context_object_name = 'request_object'

    def form_valid(self, form):
        super().form_valid(form)
        orgs = form.cleaned_data.get('organizations')
        plural = form.cleaned_data.get('plural')
        ra_objects = RequestAssignment.objects.filter(request=self.object).all()
        for ra in ra_objects:
            if ra.organization in orgs:
                ra.delete()
        for org in orgs:
            self.object.organizations.add(org)
            RequestAssignment.objects.create(
                organization=org,
                request=self.object,
                status=self.object.status
            )
            if plural:
                org = Organization.objects.filter(id=org.id).first()
                org_root = org.get_root()
                c_orgs = org_root.get_children()
                for c_org in c_orgs:
                    ra_objects = RequestAssignment.objects.filter(request=self.object, organization=c_org).all()
                    for ra in ra_objects:
                        ra.delete()
                    self.object.organizations.add(c_org)
                    RequestAssignment.objects.create(
                        organization=c_org,
                        request=self.object,
                        status=self.object.status
                    )
        self.object.save()
        set_comment(Request.EDITED)
        return HttpResponseRedirect(reverse('request-organizations', kwargs={'pk': self.object.id}))

    def has_permission(self):
        request = get_object_or_404(Request, pk=self.kwargs.get('pk'))
        can_edit_specific_org = False
        is_my_request = self.request.user == request.user
        is_supervisor = Representative.objects.filter(user=self.request.user, role=Representative.SUPERVISOR).first()
        if self.request.user.organization:
            if self.request.user.organization in request.organizations.all():
                can_edit_specific_org = True

        representatives = self.request.user.representative_set.filter(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id__isnull=False,
            user=self.request.user,
            object_id__in=[r.id for r in request.organizations.all()]
        )
        can_edit_specific_org = len(representatives) > 0
        return (is_supervisor or can_edit_specific_org or is_my_request) and has_perm(self.request.user, Action.UPDATE,
                                                                                      request)

    def handle_no_permission(self):
        messages.error(self.request, 'Šio poreikio organizacijų keisti negalite.')
        return HttpResponseRedirect(reverse('request-organizations', kwargs={'pk': self.kwargs.get('pk')}))

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio organizacijų redagavimas')
        return context_data

class RequestOrgDeleteView(PermissionRequiredMixin, RevisionMixin, DeleteView):
    model = RequestAssignment
    template_name = 'confirm_delete.html'

    def has_permission(self):
        self.object = self.get_object()
        request = get_object_or_404(Request, pk=self.object.request.pk)
        can_edit_specific_org = False
        is_my_request = self.request.user == request.user
        is_supervisor = Representative.objects.filter(user=self.request.user, role=Representative.SUPERVISOR).first()
        if self.request.user.organization:
            if self.request.user.organization in request.organizations.all():
                can_edit_specific_org = True

        representatives = self.request.user.representative_set.filter(
                content_type=ContentType.objects.get_for_model(Organization),
                object_id__isnull=False,
                user=self.request.user,
                object_id__in=[r.id for r in request.organizations.all()]
        )
        can_edit_specific_org = len(representatives) > 0
        return (is_supervisor or can_edit_specific_org or is_my_request) and has_perm(self.request.user, Action.UPDATE, request)

    def handle_no_permission(self):
        self.object = self.get_object()
        request_id = self.object.request.pk
        messages.error(self.request,'Šio poreikio organizacijų keisti negalite.')
        return HttpResponseRedirect(reverse('request-organizations', kwargs={'pk': request_id}))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        request_id = self.object.request.pk
        self.object.delete()
        return redirect(reverse('request-organizations', kwargs={'pk': request_id}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.get_object().request
        context['current_title'] = _("Termino pašalinimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[request.pk]): request.title,
        }
        return context

class RequestUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'
    context_object_name = 'request_object'

    def form_valid(self, form):
        super().form_valid(form)
        set_comment(Request.EDITED)
        return HttpResponseRedirect(self.get_success_url())

    def has_permission(self):
        request = get_object_or_404(Request, pk=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.UPDATE, request)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio redagavimas')
        return context_data


class RequestHistoryView(PlanMixin, HistoryView):
    model = Request
    detail_url_name = "request-detail"
    history_url_name = "request-history"
    tabs_template_name = 'vitrina/requests/tabs.html'
    plan_url_name = 'request-plans'


class RequestPlanView(HistoryMixin, PlanMixin, TemplateView):
    template_name = 'vitrina/requests/plans.html'
    detail_url_name = 'request-detail'
    history_url_name = 'request-plans-history'
    plan_url_name = 'request-plans'

    request_obj: Request

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get('status', 'opened')
        context['request_obj'] = self.request_obj
        if status == 'closed':
            context['plans'] = self.request_obj.planrequest_set.filter(plan__is_closed=True)
        else:
            context['plans'] = self.request_obj.planrequest_set.filter(plan__is_closed=False)
        context['can_manage_plans'] = has_perm(
            self.request.user,
            Action.PLAN,
            self.request_obj
        )
        context['selected_tab'] = status
        return context

    def get_plan_object(self):
        return self.request_obj

    def get_detail_object(self):
        return self.request_obj

    def get_history_object(self):
        return self.request_obj


class RequestCreatePlanView(PermissionRequiredMixin, RevisionMixin, TemplateView):
    template_name = 'vitrina/plans/plan_form.html'

    request_obj: Request
    organizations: List[Organization]

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        if self.request.user.is_authenticated:
            if self.request.user.is_staff or self.request.user.is_superuser:
                self.organizations = self.request_obj.organizations.all()
            else:
                self.organizations = self.request_obj.organizations.filter(
                    representatives__user=self.request.user
                )
        else:
            self.organizations = []
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.PLAN,
            self.request_obj
        ) and self.request_obj.is_not_closed()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['obj'] = self.request_obj
        context['create_form'] = PlanForm(self.request_obj, self.organizations, self.request.user)
        context['include_form'] = RequestPlanForm(self.request_obj)
        context['current_title'] = _("Įtraukti į planą")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[self.request_obj.pk]): self.request_obj.title,
            reverse('request-plans', args=[self.request_obj.pk]): _("Planas"),
        }
        return context

    def post(self, request, *args, **kwargs):
        form_type = request.POST.get('form_type')
        if form_type == 'create_form':
            form = PlanForm(self.request_obj, self.organizations, request.user, request.POST)
        else:
            form = RequestPlanForm(self.request_obj, request.POST)

        if form.is_valid():
            if form_type == 'create_form':
                plan = form.save()
                PlanRequest.objects.create(
                    plan=plan,
                    request=self.request_obj
                )
                set_comment(_(f'Pridėtas terminas "{plan}". Į terminą įtrauktas poreikis "{self.request_obj}".'))

            else:
                plan_request = form.save(commit=False)
                plan_request.request = self.request_obj
                plan_request.save()
                plan = plan_request.plan
                plan.save()
                set_comment(_(f'Į terminą "{plan}" įtrauktas poreikis "{self.request_obj}".'))

            Comment.objects.create(
                content_type=ContentType.objects.get_for_model(self.request_obj),
                object_id=self.request_obj.pk,
                user=self.request.user,
                type=Comment.PLAN,
                rel_content_type=ContentType.objects.get_for_model(plan),
                rel_object_id=plan.pk
            )
            Comment.objects.create(
                content_type=ContentType.objects.get_for_model(self.request_obj),
                object_id=self.request_obj.pk,
                user=self.request.user,
                type=Comment.STATUS,
                status=Comment.PLANNED
            )
            self.request_obj.status = Request.PLANNED
            self.request_obj.save()
            return redirect(reverse('request-plans', args=[self.request_obj.pk]))
        else:
            context = self.get_context_data(**kwargs)
            context[form_type] = form
            return render(request=request, template_name=self.template_name, context=context)


class RequestDeletePlanView(PermissionRequiredMixin, RevisionMixin, DeleteView):
    model = PlanRequest
    template_name = 'confirm_delete.html'

    def has_permission(self):
        request = self.get_object().request
        return has_perm(
            self.request.user,
            Action.PLAN,
            request
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        request_obj = self.object.request
        self.object.delete()

        plan.save()
        set_comment(_(f'Iš termino "{plan}" pašalintas poreikis "{request_obj}".'))
        return redirect(reverse('request-plans', args=[request_obj.pk]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.get_object().request
        context['current_title'] = _("Termino pašalinimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[request.pk]): request.title,
        }
        return context


class RequestDeleteDatasetView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Request
    template_name = 'confirm_remove.html'

    def dispatch(self, request, *args, **kwargs):
        self.request_object = get_object_or_404(Request, pk=self.kwargs.get('pk'))
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get('dataset_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.request_object)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('request-datasets', kwargs={'pk': self.dataset.pk}))

    def delete(self, request, *args, **kwargs):
        request_obj_items = RequestObject.objects.filter(object_id=self.dataset.pk,
                                                         content_type=ContentType.objects.get_for_model(self.dataset))
        if len(request_obj_items) > 0:
            for item in request_obj_items:
                item.delete()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('request-datasets', kwargs={'pk': self.request_object.pk})


class RequestDeletePlanDetailView(RequestDeletePlanView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object().plan.receiver
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[organization.pk]): organization.title,
        }
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        request_obj = self.object.request
        self.object.delete()

        plan.save()
        set_comment(_(f'Iš termino "{plan}" pašalintas poreikis "{request_obj}".'))
        return redirect(reverse('plan-detail', args=[plan.receiver.pk, plan.pk]))


class RequestPlansHistoryView(PlanMixin, HistoryView):
    model = Request
    detail_url_name = "request-detail"
    history_url_name = "request-plans-history"
    plan_url_name = 'request-plans'
    tabs_template_name = 'vitrina/requests/tabs.html'

    def get_history_objects(self):
        request_plan_ids = PlanRequest.objects.filter(request=self.object).values_list('plan_id', flat=True)
        return Version.objects.get_for_model(Plan).filter(
            object_id__in=list(request_plan_ids)
        ).order_by('-revision__date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[self.object.pk]): self.object.title,
        }
        return context


class RequestDatasetView(HistoryMixin, PlanMixin, ListView):
    template_name = 'vitrina/requests/datasets.html'
    detail_url_name = 'request-detail'
    history_url_name = 'request-plans-history'
    plan_url_name = 'request-plans'
    context_object_name = 'datasets'
    paginate_by = 20

    request_obj: Request

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        request_object_ids = RequestObject.objects.filter(content_type=ContentType.objects.get_for_model(Dataset),
                                                          request_id=self.request_obj.pk) \
            .values_list('object_id', flat=True)
        datasets = Dataset.objects.filter(pk__in=request_object_ids).order_by('-created')
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_obj'] = self.request_obj
        # context['datasets'] = datasets
        return context

    def get_plan_object(self):
        return self.request_obj

    def get_detail_object(self):
        return self.request_obj

    def get_history_object(self):
        return self.request_obj


class RequestOrganizationView(HistoryMixin, PlanMixin, ListView):
    template_name = 'vitrina/requests/organizations.html'
    detail_url_name = 'request-detail'
    history_url_name = 'request-plans-history'
    plan_url_name = 'request-plans'
    context_object_name = 'organizations'
    paginate_by = 20

    request_obj: Request

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            orgs = self.request.user.representative_set.filter(
                content_type=ContentType.objects.get_for_model(Organization),
                object_id__isnull=False,
            )
            org_ids = [org.id for org in orgs]
            if self.request.user.organization:
                org_ids.append(self.request.user.organization.id)
            if org_ids:
                user_org_priority = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(org_ids)])
                return RequestAssignment.objects.filter(request=self.request_obj).order_by(user_org_priority).all()
        return RequestAssignment.objects.filter(request=self.request_obj).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_obj'] = self.request_obj
        context['organizations'] = self.get_queryset()
        return context

    def get_plan_object(self):
        return self.request_obj

    def get_detail_object(self):
        return self.request_obj

    def get_history_object(self):
        return self.request_obj


class update_request_org_filters(FacetedSearchView):
    template_name = 'vitrina/datasets/organization_filter_items.html'
    form_class = RequestSearchForm
    facet_fields = RequestListView.facet_fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q')
        if q and len(q) > 2:
            facet_fields = context.get('facets').get('fields')
            form = context.get('form')
            filter_args = (self.request, form, facet_fields)
            filter = Filter(
                *filter_args,
                'organization',
                _("Organizacija"),
                Organization,
                multiple=True,
                is_int=False,
            ),
            items = []
            for item in filter[0].items():
                if q.lower() in item.title.lower():
                    items.append(item)
            extra_context = {
                'filter_items': items
            }
            context.update(extra_context)
            return context


class update_request_jurisdiction_filters(FacetedSearchView):
    template_name = 'vitrina/datasets/jurisdiction_filter_items.html'
    form_class = RequestSearchForm
    facet_fields = RequestListView.facet_fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q')
        if q and len(q) > 2:
            facet_fields = context.get('facets').get('fields')
            form = context.get('form')
            filter_args = (self.request, form, facet_fields)
            filter = Filter(
                *filter_args,
                'jurisdiction',
                _("Valdymo sritis"),
                Organization,
                multiple=True,
                is_int=False,
            ),
            items = []
            for item in filter[0].items():
                if q.lower() in item.title.lower():
                    items.append(item)
            extra_context = {
                'filter_items': items
            }
            context.update(extra_context)
            return context
