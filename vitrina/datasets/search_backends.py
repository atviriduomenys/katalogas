from haystack.backends.elasticsearch7_backend import Elasticsearch7SearchBackend, Elasticsearch7SearchEngine


def _get_default_settings():
    default_settings = Elasticsearch7SearchBackend.DEFAULT_SETTINGS
    try:
        default_settings['settings']['analysis']['analyzer'].update({
            'edgengram_search_analyzer': {
                "tokenizer": "lowercase",
            }
        })
        default_settings['settings']['analysis']['filter']['haystack_edgengram'].update({
            "min_gram": 3,
            "max_gram": 12,
        })
    except KeyError:
        pass
    return default_settings


def _get_field_mappings(backend):
    field_mappings = backend.FIELD_MAPPINGS
    try:
        field_mappings['edge_ngram'].update({
            'search_analyzer': 'edgengram_search_analyzer',
        })
    except KeyError:
        pass
    return field_mappings


class ElasticsearchBackend(Elasticsearch7SearchBackend):

    DEFAULT_SETTINGS = _get_default_settings()

    def build_schema(self, fields):
        content_field_name = ""
        mapping = self._get_common_mapping()

        for _, field_class in fields.items():
            field_mapping = _get_field_mappings(self).get(
                field_class.field_type, self.DEFAULT_FIELD_MAPPING
            ).copy()
            if field_class.boost != 1.0:
                field_mapping["boost"] = field_class.boost

            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            # Do this last to override `text` fields.
            if field_mapping["type"] == "text":
                if field_class.indexed is False or hasattr(field_class, "facet_for"):
                    field_mapping["type"] = "keyword"
                    del field_mapping["analyzer"]

            mapping[field_class.index_fieldname] = field_mapping

        return content_field_name, mapping


class ElasticSearchEngine(Elasticsearch7SearchEngine):
    backend = ElasticsearchBackend

