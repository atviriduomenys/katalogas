import re
from datetime import date

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth

WORD_PREFIX_MAX_LENGTH = 3
DEFAULT_FACET_LIMIT = 1000
TAGS_FACET_LIMIT = 50

_REGEX_SPECIAL = re.compile(r"([\\.^$*+?()\[\]{}|])")


def escape_regex(value: str) -> str:
    return _REGEX_SPECIAL.sub(r"\\\1", value)


def text_query(keyword: str, field: str = "text") -> Q:
    query = Q()
    for word in keyword.split():
        if len(word) < WORD_PREFIX_MAX_LENGTH:
            query &= Q(**{f"{field}__iregex": r"\m" + escape_regex(word)})
        else:
            query &= Q(**{f"{field}__icontains": word})
    return query


def parse_selected_facets(selected_facets: list[str]) -> list[tuple[str, str]]:
    parsed = []
    for selected_facet in selected_facets:
        if ":" not in selected_facet:
            continue
        field, value = selected_facet.split(":", 1)
        parsed.append((field.removesuffix("_exact"), value))
    return parsed


def apply_selected_facets(queryset, facet_model, fk_name: str, selected_facets: list[str]):
    for field, value in parse_selected_facets(selected_facets):
        matching = facet_model.objects.filter(field=field, value=value).values(fk_name)
        queryset = queryset.filter(pk__in=matching)
    return queryset


def facet_counts(
    queryset,
    facet_model,
    fk_name: str,
    fields: list[str],
    integer_fields: set[str] = frozenset(),
    limits: dict[str, int] | None = None,
    default_limit: int = DEFAULT_FACET_LIMIT,
) -> dict[str, list[tuple[str | int, int]]]:
    limits = limits or {}
    counts = {field: [] for field in fields}
    rows = (
        facet_model.objects.filter(**{f"{fk_name}__in": queryset.order_by().values("pk")}, field__in=fields)
        .values("field", "value")
        .annotate(count=Count(fk_name))
        .order_by("-count", "value")
    )
    for row in rows:
        field = row["field"]
        if len(counts[field]) >= limits.get(field, default_limit):
            continue
        value = int(row["value"]) if field in integer_fields else row["value"]
        counts[field].append((value, row["count"]))
    return counts


def date_facet_counts(queryset, field: str) -> list[tuple[date, int]]:
    rows = (
        queryset.order_by()
        .filter(**{f"{field}__isnull": False})
        .annotate(bucket=TruncMonth(field))
        .values("bucket")
        .annotate(count=Count("pk"))
        .order_by()
    )
    found = {row["bucket"].date().replace(day=1): row["count"] for row in rows if row["bucket"]}
    if not found:
        return []

    result = []
    year, month = min(found).year, min(found).month
    last = max(found)
    while (year, month) <= (last.year, last.month):
        bucket = date(year, month, 1)
        result.append((bucket, found.get(bucket, 0)))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result
