from django.db import connection
from haystack import connections

from unittest.mock import patch

import pytest
from django.test.utils import CaptureQueriesContext

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset


@pytest.mark.django_db
class TestDatasetIndexQuery:
    def test_dataset_index_query_count(self):
        DatasetFactory()
        DatasetFactory()
        DatasetFactory()
        DatasetFactory()
        DatasetFactory()

        ui = connections["default"].get_unified_index()
        index = ui.get_index(Dataset)

        datasets = list(index.index_queryset()[:5])

        # Bulk load tags via index method
        index._bulk_load_tags(datasets)

        docs = []
        with CaptureQueriesContext(connection) as ctx:
            with patch("haystack.backends.elasticsearch_backend.ElasticsearchSearchBackend.update", autospec=True):
                for ds in datasets:
                    docs.append(index.full_prepare(ds))

            assert len(ctx.captured_queries) == 0, f"Too many queries: {len(ctx.captured_queries)}"
