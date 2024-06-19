from haystack.backends.elasticsearch7_backend import Elasticsearch7SearchBackend, Elasticsearch7SearchEngine


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
                    'edgengram_search_analyzer': {
                        "tokenizer": "whitespace",
                        "filter": [
                            "lowercase"
                        ]
                    }
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
            'search_analyzer': 'edgengram_search_analyzer',
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


class ElasticSearchEngine(Elasticsearch7SearchEngine):
    backend = ElasticsearchBackend

