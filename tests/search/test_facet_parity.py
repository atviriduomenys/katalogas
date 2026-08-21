import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import CategoryFactory, FrequencyFactory
from vitrina.classifiers.models import AreaOfManagement
from vitrina.datasets.factories import (
    AttributionFactory,
    DatasetAttributionFactory,
    DatasetFactory,
    DatasetGroupCategoryUriFactory,
    DatasetGroupFactory,
    TypeFactory,
)
from vitrina.datasets.models import Attribution, Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request, RequestAssignment, RequestObject
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat
from vitrina.structure.models import Metadata

FACET_MODELS = {
    "organization": "orgs",
    "creator": "orgs",
    "jurisdiction": "aoms",
    "category": "categories",
    "parent_category": "categories",
    "groups": "groups",
    "frequency": "frequencies",
    "formats": "formats",
    "type": "types",
    "tags": "tags",
    "dataset_status": None,
}

IGNORED_FACET_FIELDS = {"published", "created"}


def _utc(year, month, day):
    return datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def corpus(db):
    aom_a = AreaOfManagement.objects.create(id=9001, name_lt="Sritis A", name_en="Area A")
    aom_b = AreaOfManagement.objects.create(id=9002, name_lt="Sritis B", name_en="Area B")

    org_a = OrganizationFactory(title="Org Alfa", jurisdiction=aom_a)
    org_b = OrganizationFactory(title="Org Beta", jurisdiction=aom_b)
    org_c = OrganizationFactory(title="Org Gama", jurisdiction=aom_a)

    cat_root = CategoryFactory(title="Root category")
    cat_child = cat_root.add_child(title="Child category", description="", version=1, featured=False)
    cat_other = CategoryFactory(title="Other category")

    group_x = DatasetGroupFactory()
    DatasetGroupCategoryUriFactory(group=group_x, category=cat_child, uri="group-x")

    fmt_csv = FileFormat(title="CSV", extension="CSV")
    fmt_json = FileFormat(title="JSON", extension="JSON")

    freq_daily = FrequencyFactory(title="Daily")
    freq_yearly = FrequencyFactory(title="Yearly")

    type_shown = TypeFactory(name="shown")
    type_shown.show_filter = True
    type_shown.save()
    type_hidden = TypeFactory(name="hidden")
    type_hidden.show_filter = False
    type_hidden.save()

    dataset_a = DatasetFactory(
        organization=org_a,
        title={"lt": "Rinkinys Alfa", "en": "Dataset Alpha"},
        description={"lt": "Alfa aprasymas", "en": "Alpha description"},
        status=Dataset.HAS_DATA,
        access_rights=Dataset.PUBLIC,
        frequency=freq_daily,
        published=_utc(2023, 3, 15),
        category=[cat_child],
        tags=["alpha", "shared"],
    )
    dataset_a.type.add(type_shown)
    DatasetDistributionFactory(
        dataset=dataset_a,
        title={"lt": "Ist A", "en": "Res A"},
        description={"lt": "Istekliaus A turinys", "en": "Resource A content"},
        format=fmt_csv,
    )

    dataset_b = DatasetFactory(
        organization=org_b,
        title={"lt": "Rinkinys Beta", "en": "Dataset Beta"},
        description={"lt": "Beta aprasymas", "en": "Beta description"},
        status=Dataset.INVENTORED,
        access_rights=Dataset.RESTRICTED,
        frequency=freq_yearly,
        published=_utc(2024, 7, 1),
        category=[cat_root],
        tags=["shared"],
    )
    dataset_b.type.add(type_hidden)
    DatasetDistributionFactory(
        dataset=dataset_b,
        title={"lt": "Ist B", "en": "Res B"},
        description={"lt": "Istekliaus B turinys", "en": "Resource B content"},
        format=fmt_json,
    )

    dataset_c = DatasetFactory(
        organization=org_c,
        title={"lt": "Rinkinys Gama", "en": "Dataset Gamma"},
        description={"lt": "Gama aprasymas", "en": "Gamma description"},
        status=Dataset.PLANNED,
        access_rights=Dataset.PUBLIC,
        frequency=freq_daily,
        published=_utc(2022, 11, 20),
        category=[cat_other],
        tags=["gamma"],
    )

    DatasetAttributionFactory(
        dataset=dataset_a,
        organization=org_b,
        attribution=AttributionFactory(name=Attribution.CREATOR, title="Creator"),
    )

    for dataset, level in ((dataset_a, 4), (dataset_b, 2), (dataset_c, 4)):
        Metadata.objects.filter(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id=dataset.pk,
        ).update(average_level=level)

    request_a = RequestFactory(
        dataset=dataset_a,
        status=Request.CREATED,
        translations__title_lt="Poreikis Vienas",
        translations__title_en="Request Vienas",
        translations__description_lt="Vieno aprasymas",
        translations__description_en="One description",
    )
    request_a.created = _utc(2023, 5, 10)
    request_a.save()
    RequestAssignment.objects.create(request=request_a, organization=org_a, status=Request.CREATED)
    RequestObject.objects.create(
        request=request_a,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset_a.pk,
    )

    request_b = RequestFactory(
        dataset=dataset_b,
        status=Request.APPROVED,
        translations__title_lt="Poreikis Du",
        translations__title_en="Request Du",
        translations__description_lt="Dviejo aprasymas",
        translations__description_en="Two description",
    )
    request_b.created = _utc(2024, 2, 3)
    request_b.save()
    RequestAssignment.objects.create(request=request_b, organization=org_b, status=Request.APPROVED)

    for dataset in (dataset_a, dataset_b, dataset_c):
        dataset.save()
    for request in (request_a, request_b):
        request.save()

    objects = {
        "aom_a": aom_a,
        "aom_b": aom_b,
        "org_a": org_a,
        "org_b": org_b,
        "org_c": org_c,
        "cat_root": cat_root,
        "cat_child": cat_child,
        "cat_other": cat_other,
        "group_x": group_x,
        "fmt_csv": fmt_csv,
        "fmt_json": fmt_json,
        "freq_daily": freq_daily,
        "freq_yearly": freq_yearly,
        "type_shown": type_shown,
        "type_hidden": type_hidden,
        "dataset_a": dataset_a,
        "dataset_b": dataset_b,
        "dataset_c": dataset_c,
        "request_a": request_a,
        "request_b": request_b,
    }

    def pk_map(*names):
        return {str(objects[name].pk): name for name in names}

    tag_model = dataset_a.tags.tag_model
    objects["tags"] = {name: tag_model.objects.get(name=name) for name in ("alpha", "shared", "gamma")}

    objects["names"] = {
        "tags": {str(tag.pk): name for name, tag in objects["tags"].items()},
        "orgs": pk_map("org_a", "org_b", "org_c"),
        "aoms": pk_map("aom_a", "aom_b"),
        "categories": pk_map("cat_root", "cat_child", "cat_other"),
        "groups": pk_map("group_x"),
        "frequencies": pk_map("freq_daily", "freq_yearly"),
        "formats": pk_map("fmt_csv", "fmt_json"),
        "types": pk_map("type_shown", "type_hidden"),
        "datasets": pk_map("dataset_a", "dataset_b", "dataset_c"),
        "requests": pk_map("request_a", "request_b"),
    }
    return objects


def label(names, group, value):
    if group is None:
        return str(value)
    return names[group].get(str(value), str(value))


def normalize_facets(facets, names):
    fields = {}
    for field, values in sorted((facets.get("fields") or {}).items()):
        if field in IGNORED_FACET_FIELDS:
            continue
        group = FACET_MODELS.get(field)
        fields[field] = sorted((label(names, group, value), count) for value, count in values)

    dates = {}
    for field, values in sorted((facets.get("dates") or {}).items()):
        dates[field] = [
            [value.date().isoformat() if hasattr(value, "date") else str(value), count]
            for value, count in values
            if count
        ]

    return {"fields": fields, "dates": dates}


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def assert_snapshot(name, value):
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    path = SNAPSHOT_DIR / f"{name}.json"
    serialized = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, default=str)
    if not path.exists():
        path.write_text(serialized + "\n", encoding="utf-8")
        pytest.fail(f"Snapshot {path.name} was missing. It is written now. Check it, then run the test again.")
    assert serialized == path.read_text(encoding="utf-8").rstrip("\n")


def result_names(response, names, group="datasets"):
    return sorted(label(names, group, item.pk) for item in response.context["object_list"])


def result_order(response, names, group="datasets"):
    return [label(names, group, item.pk) for item in response.context["object_list"]]


@pytest.mark.django_db
def test_dataset_list_facets(app: DjangoTestApp, corpus):
    response = app.get(reverse("dataset-list"))
    assert_snapshot("dataset_facets", normalize_facets(response.context["facets"], corpus["names"]))


@pytest.mark.django_db
def test_request_list_facets(app: DjangoTestApp, corpus):
    response = app.get(reverse("request-list"))
    assert_snapshot("request_facets", normalize_facets(response.context["facets"], corpus["names"]))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query,expected",
    [
        ("Alfa", ["dataset_a"]),
        ("Rinkinys", ["dataset_a", "dataset_b", "dataset_c"]),
        ("Alpha description", ["dataset_a"]),
        ("Org Beta", ["dataset_b"]),
        ("nomatchatall", []),
    ],
)
def test_dataset_search_query(app: DjangoTestApp, corpus, query, expected):
    response = app.get(reverse("dataset-list"), {"q": query})
    assert result_names(response, corpus["names"]) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query,expected",
    [
        ("Ga", ["dataset_c"]),
        ("am", []),
    ],
)
def test_search_of_one_or_two_characters_matches_only_a_word_start(app: DjangoTestApp, corpus, query, expected):
    response = app.get(reverse("dataset-list"), {"q": query})
    assert result_names(response, corpus["names"]) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query,expected",
    [
        ("Gam", ["dataset_c"]),
        ("ama", ["dataset_c"]),
    ],
)
def test_search_of_three_or_more_characters_matches_inside_a_word(app: DjangoTestApp, corpus, query, expected):
    response = app.get(reverse("dataset-list"), {"q": query})
    assert result_names(response, corpus["names"]) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,key,expected",
    [
        ("status", "status", ["dataset_a"]),
        ("organization", "org_b", ["dataset_b"]),
        ("jurisdiction", "aom_a", ["dataset_a", "dataset_c"]),
        ("category", "cat_child", ["dataset_a"]),
        ("parent_category", "cat_root", ["dataset_a", "dataset_b"]),
        ("groups", "group_x", ["dataset_a"]),
        ("formats", "fmt_csv", ["dataset_a"]),
        ("frequency", "freq_daily", ["dataset_a", "dataset_c"]),
        ("type", "type_shown", ["dataset_a"]),
        ("access_rights", "access_rights", ["dataset_a", "dataset_c"]),
        ("level", "level", ["dataset_a", "dataset_c"]),
    ],
)
def test_dataset_facet_filter(app: DjangoTestApp, corpus, field, key, expected):
    lookup = {
        "status": "HAS_DATA",
        "access_rights": "PUBLIC",
        "level": "4",
    }
    value = lookup.get(key) or str(corpus[key].pk)
    response = app.get(reverse("dataset-list"), {"selected_facets": f"{field}_exact:{value}"})
    assert result_names(response, corpus["names"]) == expected


@pytest.mark.django_db
def test_dataset_tag_facet_filter(app: DjangoTestApp, corpus):
    tag = corpus["tags"]["shared"]
    response = app.get(reverse("dataset-list"), {"selected_facets": f"tags_exact:{tag.pk}"})
    assert result_names(response, corpus["names"]) == ["dataset_a", "dataset_b"]


@pytest.mark.django_db
def test_dataset_facet_filter_combines_fields_with_and(app: DjangoTestApp, corpus):
    response = app.get(
        reverse("dataset-list"),
        [
            ("selected_facets", f"jurisdiction_exact:{corpus['aom_a'].pk}"),
            ("selected_facets", f"frequency_exact:{corpus['freq_daily'].pk}"),
            ("selected_facets", f"organization_exact:{corpus['org_a'].pk}"),
        ],
    )
    assert result_names(response, corpus["names"]) == ["dataset_a"]


@pytest.mark.django_db
def test_dataset_facet_filter_combines_same_field_with_and(app: DjangoTestApp, corpus):
    response = app.get(
        reverse("dataset-list"),
        [
            ("selected_facets", f"organization_exact:{corpus['org_a'].pk}"),
            ("selected_facets", f"organization_exact:{corpus['org_b'].pk}"),
        ],
    )
    assert result_names(response, corpus["names"]) == []


@pytest.mark.django_db
def test_multi_valued_facet_filter_needs_every_selected_value(app: DjangoTestApp, corpus):
    response = app.get(
        reverse("dataset-list"),
        [
            ("selected_facets", f"tags_exact:{corpus['tags']['alpha'].pk}"),
            ("selected_facets", f"tags_exact:{corpus['tags']['shared'].pk}"),
        ],
    )
    assert result_names(response, corpus["names"]) == ["dataset_a"]


@pytest.mark.django_db
def test_dataset_facet_counts_react_to_selection(app: DjangoTestApp, corpus):
    response = app.get(reverse("dataset-list"), {"selected_facets": f"jurisdiction_exact:{corpus['aom_a'].pk}"})
    counts = dict(response.context["facets"]["fields"]["organization"])
    assert counts.get(str(corpus["org_a"].pk)) == 1
    assert counts.get(str(corpus["org_c"].pk)) == 1
    assert str(corpus["org_b"].pk) not in counts


@pytest.mark.django_db
def test_dataset_date_range_filter(app: DjangoTestApp, corpus):
    response = app.get(reverse("dataset-list"), {"date_from": "2023-01-01", "date_to": "2023-12-31"})
    assert result_names(response, corpus["names"]) == ["dataset_a"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "sort,expected",
    [
        ("sort-by-date-newest", ["dataset_b", "dataset_a", "dataset_c"]),
        ("sort-by-date-oldest", ["dataset_c", "dataset_a", "dataset_b"]),
    ],
)
def test_dataset_sorting(app: DjangoTestApp, corpus, sort, expected):
    response = app.get(reverse("dataset-list"), {"sort": sort})
    assert result_order(response, corpus["names"]) == expected


@pytest.mark.django_db
def test_dataset_sort_by_title(app: DjangoTestApp, corpus):
    response = app.get(reverse("dataset-list"), {"sort": "sort-by-title"})
    assert result_order(response, corpus["names"]) == ["dataset_a", "dataset_b", "dataset_c"]


@pytest.mark.django_db
def test_request_search_and_filter(app: DjangoTestApp, corpus):
    response = app.get(reverse("request-list"), {"q": "Vienas"})
    assert result_names(response, corpus["names"], "requests") == ["request_a"]

    response = app.get(reverse("request-list"), {"selected_facets": f"organization_exact:{corpus['org_b'].pk}"})
    assert result_names(response, corpus["names"], "requests") == ["request_b"]


@pytest.mark.django_db
def test_organization_list_search_and_jurisdiction(app: DjangoTestApp, corpus):
    response = app.get(reverse("organization-list"), {"q": "Org Beta"})
    assert result_names(response, corpus["names"], "orgs") == ["org_b"]

    response = app.get(reverse("organization-list"), {"jurisdiction": str(corpus["aom_a"].pk)})
    assert result_names(response, corpus["names"], "orgs") == ["org_a", "org_c"]
