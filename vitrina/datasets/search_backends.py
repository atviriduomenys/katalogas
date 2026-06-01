from typing import Any, Iterable

from haystack.backends.elasticsearch7_backend import (
    Elasticsearch7SearchBackend,
    Elasticsearch7SearchEngine,
    Elasticsearch7SearchQuery,
)
from haystack.constants import DEFAULT_ALIAS


class ElasticsearchSearchQuery(Elasticsearch7SearchQuery):
    def __init__(self, using: str = DEFAULT_ALIAS) -> None:
        super().__init__(using=using)
        self._terms_filters: list[tuple[str, list[Any]]] = []

    def add_terms_filter(self, field: str, values: Iterable[Any]) -> None:
        self._terms_filters.append((field, list(values)))

    def _clone(self, klass: type | None = None, using: str | None = None) -> "ElasticsearchSearchQuery":
        clone = super()._clone(klass=klass, using=using)
        clone._terms_filters = list(self._terms_filters)
        return clone

    def build_params(self, spelling_query: str | None = None, **kwargs: Any) -> dict[str, Any]:
        params = super().build_params(spelling_query=spelling_query, **kwargs)
        if self._terms_filters:
            params["terms_filters"] = [(field, list(values)) for field, values in self._terms_filters]
        return params


class ElasticsearchBackend(Elasticsearch7SearchBackend):
    DEFAULT_SETTINGS = {
        "settings": {
            "index": {
                "max_ngram_diff": 2,
            },
            "analysis": {
                "analyzer": {
                    "ngram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_ngram",
                            "lowercase",
                        ],
                    },
                    "edgengram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_edgengram",
                            "lowercase",
                        ],
                    },
                    "edgengram_search_analyzer": {
                        "tokenizer": "whitespace",
                        "filter": ["lowercase"],
                    },
                },
                "filter": {
                    "haystack_ngram": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 4,
                    },
                    "haystack_edgengram": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 14,
                    },
                },
            },
        },
    }

    FIELD_MAPPINGS = {
        "edge_ngram": {
            "type": "text",
            "analyzer": "edgengram_analyzer",
            "search_analyzer": "edgengram_search_analyzer",
        },
        "ngram": {
            "type": "text",
            "analyzer": "ngram_analyzer",
        },
        "date": {"type": "date"},
        "datetime": {"type": "date"},
        "location": {"type": "geo_point"},
        "boolean": {"type": "boolean"},
        "float": {"type": "float"},
        "long": {"type": "long"},
        "integer": {"type": "long"},
    }

    def build_search_kwargs(self, query_string: str, **kwargs: Any) -> dict[str, Any]:
        terms_filters = kwargs.pop("terms_filters", None)
        search_kwargs = super().build_search_kwargs(query_string, **kwargs)
        if not terms_filters:
            return search_kwargs

        new_filters = [{"terms": {field: list(values)}} for field, values in terms_filters]

        query = search_kwargs.get("query", {})
        bool_clause = query.get("bool")

        if bool_clause and "filter" in bool_clause:
            existing = bool_clause["filter"]
            if isinstance(existing, dict) and "bool" in existing and "must" in existing["bool"]:
                existing["bool"]["must"].extend(new_filters)
            elif isinstance(existing, list):
                existing.extend(new_filters)
            else:
                bool_clause["filter"] = {"bool": {"must": [existing, *new_filters]}}
        else:
            current_query = search_kwargs.pop("query")
            wrapped_filter = new_filters[0] if len(new_filters) == 1 else {"bool": {"must": new_filters}}
            search_kwargs["query"] = {
                "bool": {
                    "must": current_query,
                    "filter": wrapped_filter,
                }
            }

        return search_kwargs


class ElasticSearchEngine(Elasticsearch7SearchEngine):
    backend = ElasticsearchBackend
    query = ElasticsearchSearchQuery
