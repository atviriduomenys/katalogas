# -*- coding: utf-8 -*-
import math
import datetime
import calendar
from typing import Optional, List, Any
from typing import Type
from typing import Tuple
from typing import Union
from typing import Dict
from urllib.parse import urlencode
from itertools import groupby
from operator import itemgetter

import markdown
from django.contrib.sites.models import Site
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.wsgi import HttpRequest
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.db.models import Model
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string, get_template
from django.template import engines, Template, Context

from vitrina import settings
from vitrina.datasets.models import Dataset
from vitrina.orgs.helpers import is_org_dataset_list
from haystack.forms import FacetedSearchForm

from crispy_forms.layout import Div, Submit
from vitrina.messages.models import EmailTemplate, SentMail
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from vitrina.messages.models import EmailTemplate
from vitrina.orgs.models import Organization
from vitrina.requests.models import Request
from vitrina.messages.models import SentMail
from django.template.loaders.app_directories import Loader


class Filter:
    name: str
    title: str
    limit: int = 10

    def __init__(
        self,
        request: HttpRequest,
        form: FacetedSearchForm,
        fields: Dict[
            str,  # Field name
            List[
                Tuple[
                    Union[str, int],  # Field value
                    int,              # Matching objects count
                ],
            ],
        ],
        name: str,
        title: str,
        model: Optional[Type[Model]] = None,
        *,
        choices: Optional[Dict] = None,
        multiple: bool = False,
        is_int: bool = True,
        # For tree-like filters
        parent: str = '',
        stats: bool = True,
        display_method: str = None,
        use_str: bool = False,
        remove_search_query: bool = False,
    ):
        self.name = name
        self.title = title
        self.request = request
        self.fields = fields
        self.model = model
        self.choices = choices
        self.form = form
        self.multiple = multiple
        self.is_int = is_int
        self.parent = parent
        self.stats = stats
        self.display_method = display_method
        self.use_str = use_str
        self.remove_search_query = remove_search_query

    def get_stats_url(self):
        path = reverse(f'dataset-stats-{self.name}')
        query = self.request.GET.urlencode()
        return f'{path}?{query}'

    def get_stats_url_request(self):
        path = reverse(f'request-stats-{self.name}')
        query = self.request.GET.urlencode()
        return f'{path}?{query}'

    def items(self):
        fields = self.fields

        selected = get_selected_value(
            self.form,
            self.name,
            self.multiple,
            self.is_int,
        )

        if self.parent:
            selected += get_selected_value(
                self.form,
                self.parent,
                self.multiple,
                self.is_int,
            )

            if selected:
                facet = fields[self.name]
            else:
                facet = fields[self.parent]

        else:
            facet = fields[self.name]
            facet = facet

        show_count = 0
        for value, count in facet:

            title = value
            if self.model and self.display_method and getattr(self.model, self.display_method):
                method = getattr(self.model, self.display_method)
                title = method(self.model, value)
            elif self.model:
                try:
                    obj = self.model.objects.get(pk=value)
                    if self.use_str:
                        title = str(obj)
                    else:
                        title = obj.title
                except ObjectDoesNotExist:
                    if value == "-1":
                        title = "Nepriskirta"
                    else:
                        continue
            elif self.choices:
                title = self.choices.get(value)

            is_selected = value in selected if self.multiple else value == selected
            yield FilterItem(
                value=value,
                title=title,
                count=count,
                selected=(
                    value in selected
                    if self.multiple else
                    value == selected
                ),
                url=get_filter_url(self.request, self.name, value, is_selected, self.remove_search_query),
                hidden=show_count > self.limit
            )
            show_count += 1


DateFacetItem = Tuple[
    datetime.datetime,  # value
    int,                # count
]


class Period:

    def facet_sort_key(self, facet_item: DateFacetItem):
        value, count = facet_item
        return self.get_value(value)

    def facet(self, facet: List[DateFacetItem]):
        facet = [
            (k, sum(c for v, c in g))
            for k, g in groupby(facet, key=self.facet_sort_key)
        ]
        facet = [(v, self.get_title(v), c) for v, c in facet]
        facet = sorted(facet, key=itemgetter(0))
        return facet

    def selected(self, date_from, date_to):
        if date_to < date_from:
            return []
        result = []
        date = date_from
        while date < date_to:
            value = self.get_value(date)
            result.append(value)
            _, date = self.get_period(value)
            date += datetime.timedelta(days=1)
        return result


class Yearly(Period):

    def get_value(self, value: datetime.datetime) -> int:
        return value.year, 'Y'

    def get_title(self, value: int) -> str:
        year, _ = value
        return str(year)

    def get_period(
        self,
        value: int,
    ) -> Tuple[datetime.date, datetime.date]:
        year, _ = value
        return (
            datetime.date(year, 1, 1),
            datetime.date(year, 12, 31)
        )


class Quarterly(Period):
    titles = {
        1: _("I ketvirtis"),
        2: _("II ketvirtis"),
        3: _("III ketvirtis"),
        4: _("IV ketvirtis"),
    }

    def get_value(self, value: datetime.datetime) -> Tuple[int, int]:
        return (value.year, math.ceil(value.month / 3), 'Q')

    def get_title(self, value: Tuple[int, int]) -> str:
        year, quarter, _ = value
        return self.titles[quarter]

    def get_period(
        self,
        value: Tuple[int, int],
    ) -> Tuple[datetime.date, datetime.date]:
        year, quarter, _ = value
        month = quarter * 3
        _, day = calendar.monthrange(year, month)
        return (
            datetime.date(year, month - 2, 1),
            datetime.date(year, month, day)
        )


class Monthly(Period):
    titles = {
        1: _("Sausis"),
        2: _("Vasaris"),
        3: _("Kovas"),
        4: _("Balandis"),
        5: _("Gegužė"),
        6: _("Birželis"),
        7: _("Liepa"),
        8: _("Rugpjūtis"),
        9: _("Rugsėjis"),
        10: _("Spalis"),
        11: _("Lapkritis"),
        12: _("Gruodis"),
    }

    def get_value(self, value: datetime.datetime) -> Tuple[int, int]:
        return (value.year, value.month, 'M')

    def get_date(self, value: Tuple[int, int]) -> datetime.date:
        year, month, _ = value
        return datetime.date(value.year, month, 1),

    def get_title(self, value: int) -> str:
        year, month, _ = value
        return self.titles[month]

    def get_period(
        self,
        value: Tuple[int, int],
    ) -> Tuple[datetime.date, datetime.date]:
        year, month, _ = value
        _, day = calendar.monthrange(year, month)
        return (
            datetime.date(year, month, 1),
            datetime.date(year, month, day)
        )


class DateFilter(Filter):
    periods = [
        Yearly(),
        Quarterly(),
        Monthly(),
    ]

    def items(self):
        fields = self.fields
        date_facet = fields[self.name]

        date_from = self.form.cleaned_data.get('date_from')
        date_to = self.form.cleaned_data.get('date_to')

        if date_from and date_to:
            facets = []
            selected = []
            for period in self.periods:
                if period_selected := period.selected(date_from, date_to):
                    period_facet = period.facet(date_facet)
                    facets.append((period, period_facet))
                    if len(period_facet) > 1:
                        # XXX: Probably better checkw would be based on
                        #      delta = date_to - date_from
                        break
                    else:
                        selected += period_selected
        else:
            period = self.periods[0]
            facets = [(period, period.facet(date_facet))]
            selected = []

        for period, facet in facets:
            for value, title, count in facet:
                start, end = period.get_period(value)
                is_selected = value in selected
                yield FilterItem(
                    value=value,
                    title=title,
                    count=count,
                    selected=is_selected,
                    url=get_date_filter_url(self.request, start, end, is_selected),
                )


class FilterItem:
    value: str
    title: str
    count: str
    selected: bool
    hidden: bool

    def __init__(
        self,
        *,
        value: str,
        title: str,
        count: int,
        selected: int,
        url: str,
        hidden: bool = False
    ):
        self.name = value
        self.value = value
        self.title = title
        self.count = count
        self.selected = selected
        self.url = url
        self.hidden = hidden


def get_selected_value(form: FacetedSearchForm, field_name: str, multiple: bool = False, is_int: bool = True) \
        -> Optional[List[Any]]:
    selected_value = [] if multiple else None
    for selected_facet in form.selected_facets:
        if selected_facet.split(":")[0] == "%s_exact" % field_name:
            if multiple:
                selected_value.append(selected_facet.split(":")[1])
            else:
                selected_value = selected_facet.split(":")[1]
                break
    if selected_value and is_int:
        try:
            selected_value = [int(val) for val in selected_value] if multiple else int(selected_value)
        except ValueError:
            return [] if multiple else None
    return selected_value


def get_filter_url(
    request: WSGIRequest,
    key: str,
    value: str,
    selected: bool = False,
    remove_search_query: bool = False
) -> str:
    query_dict = dict(request.GET.copy())
    if 'page' in query_dict:
        query_dict.pop('page')
    if remove_search_query and 'q' in query_dict:
        query_dict.pop('q')
    if selected:
        val = '%s_exact:%s' % (key, value)
        if val in query_dict.get('selected_facets', []):
            query_dict['selected_facets'].remove(val)
    else:
        if "selected_facets" in query_dict:
            query_dict["selected_facets"].append('%s_exact:%s' % (key, value))
        else:
            query_dict["selected_facets"] = "%s_exact:%s" % (key, value)
    return "?" + urlencode(query_dict, True)


def get_date_filter_url(
    request: WSGIRequest,
    start: datetime.date,
    end: datetime.date,
    selected: bool = False
) -> str:
    query_dict = dict(request.GET.copy())
    if 'page' in query_dict:
        query_dict.pop('page')
    if selected:
        val = '%s_exact:%s' % (key, value)
        if val in query_dict.get('selected_facets', []):
            query_dict['selected_facets'].remove(val)
        if is_org_dataset_list(request) and key == 'organization':
            if 'selected_facets' in query_dict:
                query_dict["selected_facets"].append('%s_exact:%s' % (key, value))
            else:
                query_dict["selected_facets"] = "%s_exact:%s" % (key, value)
    else:
        if "selected_facets" in query_dict:
            query_dict["selected_facets"].append('%s_exact:%s' % (key, value))
        else:
            query_dict["selected_facets"] = "%s_exact:%s" % (key, value)
    return "?" + urlencode(query_dict, True)


def get_date_filter_url(
    request: WSGIRequest,
    start: datetime.date,
    end: datetime.date,
    selected: bool = False
) -> str:
    query_dict = dict(request.GET.copy())
    if 'page' in query_dict:
        query_dict.pop('page')
    if selected:
        if 'date_from' in query_dict:
            query_dict.pop('date_from')
        if 'date_to' in query_dict:
            query_dict.pop('date_to')
    else:
        query_dict['date_from'] = start
        query_dict['date_to'] = end
    return "?" + urlencode(query_dict, True)


def inline_fields(*args):
    return Div(
        Div(
            *args,
            css_class="field-body",
        ), css_class="field is-horizontal",
    )


def buttons(*args):
    return Div(
        Div(*args),
        css_class="field is-grouped is-grouped-centered",
    )


def submit(title=None):
    title = title or _("Patvirtinti")
    return Submit('submit', title, css_class='button is-primary'),


def get_current_domain(request: WSGIRequest, ensure_secure=False) -> str:
    protocol = "https" if request.is_secure() or ensure_secure else "http"
    domain = Site.objects.get_current().domain
    localhost = '127.0.0.1' in domain
    if not localhost:
        return request.build_absolute_uri("%s://%s" % (protocol, domain))
    return request.build_absolute_uri(domain)


def prepare_email_by_identifier(email_identifier, base_template_content, email_title_subject, email_template_keys):
    email_template = EmailTemplate.objects.filter(identifier=email_identifier)
    if not email_template:
        email_subject = email_title = email_title_subject
        email_content = base_template_content.format(*email_template_keys)
        created_template = EmailTemplate.objects.create(
            created=datetime.datetime.now(),
            version=0,
            identifier=email_identifier,
            template=base_template_content,
            subject=_(email_title_subject),
            title=_(email_title)
        )
        created_template.save()
    else:
        email_template = email_template.first()
        email_content = str(email_template.template)
        email_content = email_content.format(*email_template_keys)
        email_subject = str(email_template.subject)

    return {'email_content': email_content, 'email_subject': email_subject}


def _get_email_tempate_from_db(name: str) -> EmailTemplate | None:
    try:
        return EmailTemplate.objects.get(identifier=name)
    except EmailTemplate.DoesNotExist:
        return None


def email(
    recipients: list[str],
    email_identifier: str,
    name: str,  # template name
    context: dict[str, Any] | None = None,
    *,
    # Allow user to override email templates via Admin.
    override: bool = True,
) -> dict[str, str]:
    context = context or {}
    email_template = None
    subject = None
    if override:
        email_template = _get_email_tempate_from_db(email_identifier)
    if email_template:
        subject_template = email_template.subject
        subject_template = Template(subject_template)
        subject_context = Context(context)
        subject = subject_template.render(subject_context)

        template_db = email_template.template
        template = Template(template_db)
        context = Context(context)
        content = template.render(context)
        html_message = markdown.markdown(content)
    else:
        template_path = get_template(name)
        with open(template_path.origin.name, encoding="utf-8") as file:
            read_data = file.readlines()
        content = render_to_string(name, context)
        html_message = markdown.markdown(content)
        html_message = '\n'.join(html_message.splitlines()[1:])
        send_email_title = content.splitlines()
        content_to_save = markdown.markdown(''.join(read_data[2:]))
        EmailTemplate.objects.create(
            created=datetime.datetime.now(),
            version=0,
            identifier=email_identifier,
            template=content_to_save,
            subject=read_data[0].splitlines()[0],
            title=read_data[0].splitlines()[0]
        )
    try:
        send_mail(
            subject=subject if subject else send_email_title[0],
            message=str(content),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
        )
        email_send = True
    except Exception as e:
        import logging
        logging.warning("Email was not sent", send_email_title[0],
                        _(str(content)), recipients, e)
        email_send = False

    SentMail.objects.create(
        created=datetime.datetime.now(),
        deleted=None,
        deleted_on=None,
        modified=datetime.datetime.now(),
        version=0,
        recipient=list(recipients),
        email_subject=subject,
        email_content=content,
        email_sent=email_send
    )


def send_email_with_logging(email_data, email_list):
    try:
        send_mail(
            subject=email_data['email_subject'],
            message=email_data['email_content'],
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=email_list,
        )
    except Exception as e:
        import logging
        logging.warning("Email was not sent", email_data['email_subject'],
                        email_data['email_content'], email_list, e)


def get_stats_filter_options_based_on_model(model, duration, sorting, indicator, filter=None):
    duration = {
        'selected': duration,
        'label': _("Laikotarpis"),
        'fields': [
            {'value': 'duration-yearly', 'label': _("Kas metus")},
            {'value': 'duration-quarterly', 'label': _("Kas ketvirtį")},
            {'value': 'duration-monthly', 'label': _("Kas mėnesį")},
            {'value': 'duration-weekly', 'label': _("Kas savaitę")},
            {'value': 'duration-daily', 'label': _("Kas dieną")}
        ],
    }
    sort = {
            'selected': sorting,
            'label': _("Rūšiuoti"),
            'fields': [
                {'value': 'sort-year-desc', 'label': _("Naujausi")},
                {'value': 'sort-year-asc', 'label': _("Seniausi")},
            ] if indicator == 'publication' else [
                {'value': 'sort-asc', 'label': _("Mažiausias rodiklis")},
                {'value': 'sort-desc', 'label': _("Didžiausias rodiklis")},
            ]
        }
    active_indicator = {
        'selected': indicator,
        'label': _("Rodiklis"),
    }
    if model is Request:
        active_indicator.update({
                'fields': [
                    {'value': 'request-count', 'label': _("Poreikių skaičius")},
                    {'value': 'request-count-open', 'label': _("Poreikių skaičius (neatsakytų)")},
                    {'value': 'request-count-late', 'label': _("Poreikių skaičius (vėluojančių)")},
                ]
            })
    if model is Dataset and filter:
        active_indicator.update({
            'fields': [
                {'value': 'download-request-count', 'label': _("Atsisiuntimų (užklausų) skaičius")},
                {'value': 'download-object-count', 'label': _("Atsisiuntimų (objektų) skaičius")},
                {'value': 'object-count', 'label': _("Objektų skaičius")},
                {'value': 'field-count', 'label': _("Savybių (duomenų laukų) skaičius")},
                {'value': 'model-count', 'label': _("Esybių (modelių) skaičius")},
                {'value': 'distribution-count', 'label': _("Duomenų šaltinių (distribucijų) skaičius")},
                {'value': 'dataset-count', 'label': _("Duomenų rinkinių skaičius")},
                {'value': 'request-count', 'label': _("Poreikių skaičius")},
                {'value': 'project-count', 'label': _("Projektų skaičius")},
            ] + ([{'value': 'level-average', 'label': _("Brandos lygis (vidurkis)")}] if filter != 'level' else [])
        })
    if model is Organization:
        active_indicator.update({
            'fields': [
                {'value': 'organization-count', 'label': _("Organizacijų skaičius (pavaldžių)")},
                {'value': 'coordinator-count', 'label': _("Koordinatorių skaičius")},
                {'value': 'representative-count', 'label': _("Tvarkytojų skaičius")},
            ]
        })
    return {
        'duration': duration,
        'sort': sort,
        'indicator': active_indicator
    }


def none_to_string(value):
    if value is None:
        return ""
    return value


def object_to_none(obj):
    if not obj or not obj.pk:
        return None
    return obj
