import pytest
from haystack.query import SearchQuerySet

from vitrina.datasets.search_backends import (
    ElasticsearchBackend,
    ElasticSearchEngine,
    ElasticsearchSearchQuery,
)
from vitrina.datasets.services import apply_terms_filter


@pytest.fixture
def backend():
    return ElasticsearchBackend(
        connection_alias="default",
        URL="http://localhost:9200/",
        INDEX_NAME="test",
    )


@pytest.mark.django_db
def test_add_terms_filter_records_field_and_values():
    query = ElasticsearchSearchQuery(using="default")
    query.add_terms_filter("django_id", [1, 2, 3])
    assert query._terms_filters == [("django_id", [1, 2, 3])]


@pytest.mark.django_db
def test_add_terms_filter_normalises_values_to_list():
    query = ElasticsearchSearchQuery(using="default")
    query.add_terms_filter("django_id", iter([1, 2, 3]))
    assert query._terms_filters == [("django_id", [1, 2, 3])]


@pytest.mark.django_db
def test_clone_preserves_terms_filters_independently():
    query = ElasticsearchSearchQuery(using="default")
    query.add_terms_filter("django_id", [1, 2])
    clone = query._clone()
    clone.add_terms_filter("organization", [9])
    assert query._terms_filters == [("django_id", [1, 2])]
    assert clone._terms_filters == [("django_id", [1, 2]), ("organization", [9])]


@pytest.mark.django_db
def test_build_params_includes_terms_filters_when_present():
    query = ElasticsearchSearchQuery(using="default")
    query.add_terms_filter("django_id", [1, 2])
    params = query.build_params()
    assert params["terms_filters"] == [("django_id", [1, 2])]


@pytest.mark.django_db
def test_build_params_omits_key_when_no_terms_filters():
    query = ElasticsearchSearchQuery(using="default")
    params = query.build_params()
    assert "terms_filters" not in params


@pytest.mark.django_db
def test_build_search_kwargs_appends_terms_filter(backend):
    body = backend.build_search_kwargs(
        "*:*",
        terms_filters=[("django_id", ["1", "2", "3"])],
    )

    bool_clause = body["query"]["bool"]
    flt = bool_clause["filter"]

    if isinstance(flt, dict) and "terms" in flt:
        assert flt["terms"] == {"django_id": ["1", "2", "3"]}
    else:
        terms_clauses = [f for f in flt["bool"]["must"] if "terms" in f and f["terms"].get("django_id")]
        assert terms_clauses == [{"terms": {"django_id": ["1", "2", "3"]}}]


@pytest.mark.django_db
def test_build_search_kwargs_passes_through_when_no_terms_filters(backend):
    body = backend.build_search_kwargs("*:*")

    def _terms_field_names(node):
        names = set()
        if isinstance(node, dict):
            if "terms" in node and isinstance(node["terms"], dict):
                names.update(node["terms"].keys())
            for value in node.values():
                names.update(_terms_field_names(value))
        elif isinstance(node, list):
            for item in node:
                names.update(_terms_field_names(item))
        return names

    field_names = _terms_field_names(body)
    user_fields = {f for f in field_names if f != "django_ct"}
    assert user_fields == set()


@pytest.mark.django_db
def test_build_search_kwargs_supports_multiple_terms_filters(backend):
    body = backend.build_search_kwargs(
        "*:*",
        terms_filters=[("django_id", ["1", "2"]), ("organization", ["9"])],
    )

    flt = body["query"]["bool"]["filter"]
    inner = flt["bool"]["must"] if "bool" in flt else [flt]
    fields_seen = {next(iter(f["terms"])) for f in inner if "terms" in f}
    assert {"django_id", "organization"}.issubset(fields_seen)


@pytest.mark.django_db
def test_engine_uses_custom_search_query():
    assert ElasticSearchEngine.query is ElasticsearchSearchQuery


@pytest.mark.django_db
def test_apply_terms_filter_returns_clone_with_recorded_filter():
    sqs = SearchQuerySet()
    new_sqs = apply_terms_filter(sqs, "django_id", [1, 2, 3])

    assert new_sqs is not sqs
    assert getattr(sqs.query, "_terms_filters", []) == []
    assert new_sqs.query._terms_filters == [("django_id", [1, 2, 3])]
