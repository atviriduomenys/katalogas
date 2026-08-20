# -*- coding: utf-8 -*-
import math
import datetime
import calendar
import logging
import mimetypes
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Optional, List, Any
from typing import Type
from typing import Tuple
from typing import Union
from typing import Dict
from urllib.parse import urlencode
from itertools import groupby
from operator import itemgetter

try:
    import magic
except (ImportError, OSError):
    magic = None
import markdown
from django.apps import apps
from django.contrib.sites.models import Site
from django.core.files import File
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.wsgi import HttpRequest
from django.core.mail import send_mail
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _
from django.db.models import Model
from django.urls import reverse
from django.template.loader import get_template
from django.template import Template, Context
from filer.validation import FileValidationError, validate_upload

from vitrina import settings
from vitrina.datasets.models import Dataset
from vitrina.search.forms import SearchForm

from crispy_forms.layout import Div, Submit
from vitrina.messages.models import EmailTemplate, SentMail
from vitrina.orgs.models import Organization
from vitrina.requests.models import Request
from vitrina.structure.models import Model as StructureModel, Property as StructureProperty

logger = logging.getLogger(__name__)


class Filter:
    name: str
    title: str
    limit: int = 10

    def __init__(
        self,
        request: HttpRequest,
        form: SearchForm,
        fields: Dict[
            str,  # Field name
            List[
                Tuple[
                    Union[str, int],  # Field value
                    int,  # Matching objects count
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
        parent: str = "",
        stats: bool = True,
        display_method: str = None,
        use_str: bool = False,
        remove_search_query: bool = False,
        order: classmethod = None,
        expand: bool = True,
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
        self.order = order
        self.expand = expand

    def get_stats_url(self):
        path = reverse(f"dataset-stats-{self.name}")
        query = self.request.GET.urlencode()
        return f"{path}?{query}"

    def get_stats_url_request(self):
        path = reverse(f"request-stats-{self.name}")
        query = self.request.GET.urlencode()
        return f"{path}?{query}"

    def items(self):
        fields = self.fields
        if not fields:
            return

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

        if self.order:
            facet = self.order(facet)

        objects_by_pk = {}
        if self.model and not self.display_method:
            objects_by_pk = {
                str(obj.pk): obj for obj in self.model.objects.filter(pk__in=[value for value, _ in facet])
            }

        show_count = 1
        for value, count in facet:
            title = value
            if self.model and self.display_method and getattr(self.model, self.display_method):
                method = getattr(self.model, self.display_method)
                title = method(self.model, value)
            elif self.model:
                obj = objects_by_pk.get(str(value))
                if obj is not None:
                    title = str(obj) if self.use_str else obj.title
                elif value == "-1":
                    title = "Nepriskirta"
                else:
                    continue
            elif self.choices:
                title = self.choices.get(value)
                if not title:
                    continue

            is_selected = value in selected if self.multiple else value == selected
            yield FilterItem(
                value=value,
                title=title,
                count=count,
                selected=(value in selected if self.multiple else value == selected),
                url=get_filter_url(
                    self.request,
                    self.name,
                    value,
                    is_selected,
                    self.remove_search_query,
                ),
                hidden=show_count > self.limit,
            )
            show_count += 1

    def length(self):
        fields = self.fields
        facet = fields[self.name]
        return len(facet)


DateFacetItem = Tuple[
    datetime.datetime,  # value
    int,  # count
]


class Period:
    def facet_sort_key(self, facet_item: DateFacetItem):
        value, count = facet_item
        return self.get_value(value)

    def facet(self, facet: List[DateFacetItem]):
        facet = [(k, sum(c for v, c in g)) for k, g in groupby(facet, key=self.facet_sort_key)]
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
        return value.year, "Y"

    def get_title(self, value: int) -> str:
        year, _ = value
        return str(year)

    def get_period(
        self,
        value: int,
    ) -> Tuple[datetime.date, datetime.date]:
        year, _ = value
        return (datetime.date(year, 1, 1), datetime.date(year, 12, 31))


class Quarterly(Period):
    titles = {
        1: _("I ketvirtis"),
        2: _("II ketvirtis"),
        3: _("III ketvirtis"),
        4: _("IV ketvirtis"),
    }

    def get_value(self, value: datetime.datetime) -> Tuple[int, int]:
        return (value.year, math.ceil(value.month / 3), "Q")

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
        return (datetime.date(year, month - 2, 1), datetime.date(year, month, day))


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
        return (value.year, value.month, "M")

    def get_date(self, value: Tuple[int, int]) -> datetime.date:
        year, month, _ = value
        return (datetime.date(value.year, month, 1),)

    def get_title(self, value: int) -> str:
        year, month, _ = value
        return self.titles[month]

    def get_period(
        self,
        value: Tuple[int, int],
    ) -> Tuple[datetime.date, datetime.date]:
        year, month, _ = value
        _, day = calendar.monthrange(year, month)
        return (datetime.date(year, month, 1), datetime.date(year, month, day))


class DateFilter(Filter):
    periods = [
        Yearly(),
        Quarterly(),
        Monthly(),
    ]

    def items(self):
        fields = self.fields
        date_facet = fields[self.name]

        date_from = self.form.cleaned_data.get("date_from")
        date_to = self.form.cleaned_data.get("date_to")

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
        hidden: bool = False,
    ):
        self.name = value
        self.value = value
        self.title = title
        self.count = count
        self.selected = selected
        self.url = url
        self.hidden = hidden


def get_selected_value(
    form: SearchForm,
    field_name: str,
    multiple: bool = False,
    is_int: bool = True,
) -> Optional[List[Any]]:
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
    remove_search_query: bool = False,
    facet_field: bool = True,
) -> str:
    query_dict = dict(request.GET.copy())
    if "page" in query_dict:
        query_dict.pop("page")
    if remove_search_query and "q" in query_dict:
        query_dict.pop("q")

    if facet_field:
        if selected:
            val = "%s_exact:%s" % (key, value)
            if val in query_dict.get("selected_facets", []):
                query_dict["selected_facets"].remove(val)
        else:
            if "selected_facets" in query_dict:
                query_dict["selected_facets"].append("%s_exact:%s" % (key, value))
            else:
                query_dict["selected_facets"] = "%s_exact:%s" % (key, value)
    else:
        if selected and value in query_dict.get(key, []):
            query_dict[key].remove(value)
        else:
            query_dict[key] = value
    return "?" + urlencode(query_dict, True)


def get_date_filter_url(
    request: WSGIRequest,
    start: datetime.date,
    end: datetime.date,
    selected: bool = False,
) -> str:
    query_dict = dict(request.GET.copy())
    if "page" in query_dict:
        query_dict.pop("page")
    if selected:
        if "date_from" in query_dict:
            query_dict.pop("date_from")
        if "date_to" in query_dict:
            query_dict.pop("date_to")
    else:
        query_dict["date_from"] = start
        query_dict["date_to"] = end
    return "?" + urlencode(query_dict, True)


def inline_fields(*args):
    return Div(
        Div(
            *args,
            css_class="field-body",
        ),
        css_class="field is-horizontal",
    )


def buttons(*args):
    return Div(
        Div(*args),
        css_class="field is-grouped is-grouped-centered",
    )


def submit(title=None):
    title = title or _("Patvirtinti")
    return (Submit("submit", title, css_class="button is-primary"),)


def get_current_domain(request: HttpRequest, ensure_secure=False) -> str:
    protocol = "https" if request.is_secure() or ensure_secure else "http"
    domain = Site.objects.get_current().domain
    localhost = "127.0.0.1" in domain
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
            title=_(email_title),
        )
        created_template.save()
    else:
        email_template = email_template.first()
        email_content = str(email_template.template)
        email_content = email_content.format(*email_template_keys)
        email_subject = str(email_template.subject)

    return {"email_content": email_content, "email_subject": email_subject}


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

        subject_template_text = read_data[0].splitlines()[0]
        subject_template = Template(subject_template_text)
        subject_context = Context(context)
        subject = subject_template.render(subject_context)

        content_to_save = markdown.markdown("".join(read_data[2:]))
        template = Template(content_to_save)
        context = Context(context)
        content = template.render(context)
        html_message = markdown.markdown(content)

        EmailTemplate.objects.create(
            version=0,
            identifier=email_identifier,
            template=content_to_save,
            subject=subject_template_text,
            title=subject_template_text,
        )
    try:
        send_mail(
            subject=subject,
            message=str(content),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
        )
        email_send = True
    except Exception as e:
        logger.warning(
            "Email was not sent: subject=%s recipients=%s error=%s",
            subject,
            recipients,
            e,
            exc_info=True,
        )
        email_send = False

    SentMail.objects.create(
        deleted=None,
        deleted_on=None,
        version=0,
        recipient=list(recipients),
        email_subject=subject,
        email_content=content,
        email_sent=email_send,
        identifier=email_identifier,
    )


def send_email_with_logging(email_data, email_list):
    try:
        send_mail(
            subject=email_data["email_subject"],
            message=email_data["email_content"],
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=email_list,
        )
    except Exception as e:
        logger.warning(
            "Email was not sent: subject=%s recipients=%s error=%s",
            email_data["email_subject"],
            email_list,
            e,
            exc_info=True,
        )


def get_stats_filter_options_based_on_model(model, duration, sorting, indicator, filter=None):
    duration = {
        "selected": duration,
        "label": _("Laikotarpis"),
        "fields": [
            {"value": "duration-yearly", "label": _("Kas metus")},
            {"value": "duration-quarterly", "label": _("Kas ketvirtį")},
            {"value": "duration-monthly", "label": _("Kas mėnesį")},
            {"value": "duration-weekly", "label": _("Kas savaitę")},
            {"value": "duration-daily", "label": _("Kas dieną")},
        ],
    }
    sort = {
        "selected": sorting,
        "label": _("Rūšiuoti"),
        "fields": [
            {"value": "sort-year-desc", "label": _("Naujausi")},
            {"value": "sort-year-asc", "label": _("Seniausi")},
        ]
        if indicator == "publication"
        else [
            {"value": "sort-asc", "label": _("Mažiausias rodiklis")},
            {"value": "sort-desc", "label": _("Didžiausias rodiklis")},
        ],
    }
    active_indicator = {
        "selected": indicator,
        "label": _("Rodiklis"),
    }
    if model is Request:
        active_indicator.update(
            {
                "fields": [
                    {"value": "request-count", "label": _("Poreikių skaičius")},
                    {
                        "value": "request-count-open",
                        "label": _("Poreikių skaičius (neatsakytų)"),
                    },
                    {
                        "value": "request-count-late",
                        "label": _("Poreikių skaičius (vėluojančių)"),
                    },
                ]
            }
        )
    if model is Dataset and filter:
        active_indicator.update(
            {
                "fields": [
                    {
                        "value": "download-request-count",
                        "label": _("Atsisiuntimų (užklausų) skaičius"),
                    },
                    {
                        "value": "download-object-count",
                        "label": _("Atsisiuntimų (objektų) skaičius"),
                    },
                    {"value": "object-count", "label": _("Objektų skaičius")},
                    {
                        "value": "field-count",
                        "label": _("Savybių (duomenų laukų) skaičius"),
                    },
                    {"value": "model-count", "label": _("Esybių (modelių) skaičius")},
                    {
                        "value": "distribution-count",
                        "label": _("Pateikčių skaičius"),
                    },
                    {"value": "dataset-count", "label": _("Duomenų išteklių skaičius")},
                    {"value": "request-count", "label": _("Poreikių skaičius")},
                    {"value": "project-count", "label": _("Projektų skaičius")},
                ]
                + ([{"value": "level-average", "label": _("Brandos lygis (vidurkis)")}] if filter != "level" else [])
            }
        )
    if model is Organization:
        active_indicator.update(
            {
                "fields": [
                    {
                        "value": "organization-count",
                        "label": _("Organizacijų skaičius (pavaldžių)"),
                    },
                    {
                        "value": "coordinator-count",
                        "label": _("Koordinatorių skaičius"),
                    },
                    {
                        "value": "representative-count",
                        "label": _("Tvarkytojų skaičius"),
                    },
                ]
            }
        )
    return {"duration": duration, "sort": sort, "indicator": active_indicator}


def none_to_string(value):
    if value is None:
        return ""
    return value


def object_to_none(obj):
    if not obj or not obj.pk:
        return None
    return obj


def get_encoding(file_path):
    with open(file_path, mode="rb") as f:
        mark = f.readline(3)
        if mark == b"\xef\xbb\xbf":
            return "utf-8-sig"
        else:
            return "utf-8"


def _detect_content_type(file) -> Optional[str]:
    """Sniff the real MIME type from the file's bytes using libmagic.

    Returns None for empty files (nothing to sniff). If reading or libmagic
    fails, this fails closed: the failure is logged and a FileValidationError is
    raised so the upload is rejected with a user-visible message instead of
    silently skipping the content-based defense-in-depth check (which would let
    spoofed content through when libmagic is missing or misconfigured).
    """
    try:
        try:
            file.seek(0)
            header = file.read(2048)
        except Exception:
            logger.exception("Could not read uploaded file for content-type sniffing")
            raise FileValidationError(_("Nepavyko perskaityti įkelto failo turinio."))

        if not header:
            return None

        if magic is None:
            logger.error("python-magic/libmagic is not available; rejecting upload")
            raise FileValidationError(
                _("Nepavyko patikrinti failo turinio tipo. Kreipkitės į sistemos administratorių.")
            )

        try:
            detected = magic.from_buffer(header, mime=True)
        except Exception:
            logger.exception("libmagic content-type sniffing failed")
            raise FileValidationError(
                _("Nepavyko patikrinti failo turinio tipo. Kreipkitės į sistemos administratorių.")
            )
        return detected.split(";", 1)[0].strip().lower()
    finally:
        # Best-effort: leave the read cursor at the start for downstream
        # validators/handlers, on the success and failure paths alike.
        try:
            file.seek(0)
        except Exception:
            pass


def _run_deny_validators(file_name: str, file, mime_type: str) -> None:
    """Run only the configured deny/scan validators for ``mime_type``.

    Unlike filer.validation.validate_upload this deliberately skips the MIME
    whitelist gate: it is used with the *sniffed* content type, where harmless
    detections (e.g. a .docx sniffing as application/zip, a legacy .doc as an OLE
    container) must not be rejected. Only types with a deny/scan rule are blocked.

    The rules come from filer's effective, resolved validator registry
    (app config ``FILE_VALIDATORS``) rather than settings.FILER_ADD_FILE_VALIDATORS
    directly. That registry is filer's built-in validators, minus the ones we
    drop via FILER_REMOVE_FILE_VALIDATORS and plus the project's
    FILER_ADD_FILE_VALIDATORS (see the upload-security block in settings.py for
    which defaults are kept vs removed). Reading the resolved registry here keeps
    this defense-in-depth pass byte-for-byte consistent with the rules filer's own
    validate_upload applies on the declared-type gate.
    """
    validators = apps.get_app_config("filer").FILE_VALIDATORS.get(mime_type, [])
    try:
        for validator in validators:
            file.seek(0)
            validator(file_name, file, None, mime_type)
    finally:
        # Reset the cursor even when a validator rejects the file, so upstream
        # error handling sees the file object at position 0.
        try:
            file.seek(0)
        except Exception:
            pass


def validate_file(file: File) -> None:
    # Register MIME types the portal whitelists that Python's built-in registry
    # does not know (or maps differently), so the declared-type gate is
    # deterministic regardless of the host's /etc/mime.types (e.g. a slim
    # container image has a much smaller table than a dev machine). Extensions
    # that mimetypes treats as *encodings* (.gz, .bz2) cannot be registered this
    # way; they are handled via the encoding fallback below.
    mimetypes.add_type("text/asciidoc", ".adoc")  # ADOC
    mimetypes.add_type("image/webp", ".webp")  # webp
    mimetypes.add_type("application/geo+json", ".geojson")  # GeoJSON
    mimetypes.add_type("application/ld+json", ".jsonld")  # JSON-LD
    mimetypes.add_type("application/rdf+xml", ".rdf")  # RDF/XML
    mimetypes.add_type("text/turtle", ".ttl")  # Turtle
    mimetypes.add_type("application/n-triples", ".nt")  # N-Triples
    mimetypes.add_type("text/n3", ".n3")  # N3
    mimetypes.add_type("text/tab-separated-values", ".tsv")  # TSV
    mimetypes.add_type("application/x-7z-compressed", ".7z")  # 7z
    # Security: pin XHTML to application/xhtml+xml so it reliably hits the deny
    # rule, instead of falling back to a whitelisted type (e.g. application/xml)
    # or an unregistered None on hosts with a different mimetypes table.
    mimetypes.add_type("application/xhtml+xml", ".xhtml")  # XHTML
    mimetypes.add_type("application/xhtml+xml", ".xht")  # XHTML

    # First gate: validate by the declared (extension-based) MIME type. This runs
    # the FILER_MIME_TYPE_WHITELIST check followed by the deny validators.
    guessed_mime, guessed_encoding = mimetypes.guess_type(file.name)
    if guessed_mime is None and guessed_encoding:
        # mimetypes reports .gz/.bz2 as an encoding with no type, so guess_type
        # can never return application/gzip or application/x-bzip2 for them (and
        # add_type does not help). Map the whitelisted archive encodings here so a
        # standalone .gz/.bz2 is not wrongly rejected as application/octet-stream.
        guessed_mime = {
            "gzip": "application/gzip",
            "bzip2": "application/x-bzip2",
        }.get(guessed_encoding)
    declared_mime = guessed_mime or "application/octet-stream"
    validate_upload(
        file_name=file.name,
        file=file.file,
        owner=None,
        mime_type=declared_mime,
    )

    # Defense in depth: sniff the actual content type and re-run the deny
    # validators against it. This catches active content (HTML/PHP/shell/SVG/
    # executables) smuggled past the extension gate under a benign extension.
    detected_mime = _detect_content_type(file.file)
    if detected_mime and detected_mime != declared_mime:
        _run_deny_validators(file.name, file.file, detected_mime)


def get_file_extension(file_name: str) -> str:
    return Path(file_name).suffix[1:]


def build_page_title_context(
    *,
    dataset: Dataset | None = None,
    organization: Organization | None = None,
    model: StructureModel | None = None,
    prop: StructureProperty | None = None,
    language_code: str = "lt",
) -> dict[str, str]:
    """Build page title context based on the provided objects."""

    context: dict[str, str] = {}

    if organization:
        context["title"] = organization.title
        context["object_type"] = _("Organizacija")
        return context

    if not dataset:
        return context

    _add_common_dataset_context(context, dataset, language_code)

    if prop and model:
        context["title"] = getattr(prop, "title", None) or prop.name
        context["object_type"] = _("Modelio laukas")
    elif model:
        context["title"] = getattr(model, "title", None) or model.name
        context["object_type"] = _("Modelis")
    else:
        title = dataset.safe_translation_getter("title", language_code=language_code) or ""
        context["title"] = title
        context["object_type"] = dataset.subclass.translated_title if dataset.subclass else ""

    return context


def _add_common_dataset_context(context: dict[str, str], dataset: Dataset, language_code: str) -> None:
    """Add common context elements that are shared across dataset-based objects."""
    try:
        parent_dataset = _get_parent_dataset(dataset)
        context["root_label"] = _("Duomenų skelbėjas")
        context["root_name"] = parent_dataset.organization.title
    except Exception:
        pass

    info_title = _find_information_system_title(dataset, language_code)
    if info_title:
        context["info_system_label"] = _("Informacinė sistema")
        context["info_system_name"] = info_title


def _find_information_system_title(dataset: Dataset, language_code: str) -> str | None:
    """Given a dataset and language, return title of any parent dataset that is an
    Information System. Returns None if the current dataset itself is an Information System.
    """

    if dataset.subclass and getattr(dataset.subclass, "is_information_system", False):
        return None

    try:
        part_of_qs = dataset.part_of.all()
    except Exception:
        part_of_qs = []

    for rel in part_of_qs:
        try:
            parent = rel.part_of
        except Exception:
            parent = None
        if parent and parent.subclass and getattr(parent.subclass, "is_information_system", False):
            return parent.safe_translation_getter("title", language_code=language_code) or parent.title

    # Fallback: Use MP Node logic to traverse up the tree
    ancestors = dataset.get_ancestors()
    for ancestor in ancestors:
        if ancestor.subclass and getattr(ancestor.subclass, "is_information_system", False):
            return ancestor.safe_translation_getter("title", language_code=language_code) or ancestor.title
        current = dataset
        while current.get_parent():
            current = current.get_parent()
            if current.subclass and getattr(current.subclass, "is_information_system", False):
                return current.safe_translation_getter("title", language_code=language_code) or current.title
    return None


def _get_parent_dataset(dataset: Dataset) -> Dataset:
    ancestor = dataset.get_ancestors().select_related("organization").first()
    return ancestor or dataset


def join_br(fmt: str, values: Iterable[Sequence[Any]]) -> SafeString:
    return format_html_join(mark_safe("<br/>"), fmt, values)
