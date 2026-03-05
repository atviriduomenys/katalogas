from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from elasticsearch.exceptions import NotFoundError
from haystack import connections
from unittest.mock import patch

import pytest

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.structure.factories import ModelFactory, PropertyFactory


@pytest.mark.django_db
class TestDatasetIndexQuery:
    QUERY_COUNT_THRESHOLD = 28

    def test_bulk_index_query_count(self):
        datasets_to_create = 5
        for _ in range(datasets_to_create):
            dataset = DatasetFactory()
            DatasetDistributionFactory(dataset=dataset)
            model = ModelFactory(metadata_version__dataset=dataset)
            PropertyFactory(model=model, metadata_version=model.metadata_version)
            RequestFactory(dataset=dataset)
            ProjectFactory(datasets=[dataset])

        ui = connections["default"].get_unified_index()
        index = ui.get_index(Dataset)

        with CaptureQueriesContext(connection) as ctx:
            datasets = list(index.index_queryset()[:5])

            with patch("haystack.backends.elasticsearch_backend.ElasticsearchSearchBackend.update"):
                for ds in datasets:
                    index.full_prepare(ds)

        query_count = len(ctx.captured_queries)

        assert query_count <= self.QUERY_COUNT_THRESHOLD, f"Too many queries for bulk indexing: {query_count}"

        # Verify batch queries use IN clauses (not individual lookups)
        in_clause_queries = sum(1 for q in ctx.captured_queries if " IN (" in q["sql"])
        assert in_clause_queries >= 5, "Expected batch queries with IN clauses"

    def test_single_object_update_query_count(self):
        dataset = DatasetFactory()

        ui = connections["default"].get_unified_index()
        index = ui.get_index(Dataset)

        fresh_instance = Dataset.objects.get(pk=dataset.pk)

        with CaptureQueriesContext(connection) as ctx:
            with patch("haystack.backends.elasticsearch_backend.ElasticsearchSearchBackend.update"):
                index.update_object(fresh_instance)

        query_count = len(ctx.captured_queries)

        assert query_count <= self.QUERY_COUNT_THRESHOLD, f"Too many queries for single object update: {query_count}"

    def test_index_queryset_excludes_datasets_without_title(self):
        dataset_with_title = DatasetFactory()
        dataset_without_title = DatasetFactory()
        dataset_without_title.translations.all().delete()

        ui = connections["default"].get_unified_index()
        index = ui.get_index(Dataset)

        indexed_pks = list(index.index_queryset().values_list("pk", flat=True))

        assert dataset_with_title.pk in indexed_pks
        assert dataset_without_title.pk not in indexed_pks

    def test_index_queryset_uses_exists_subquery(self):
        DatasetFactory()

        ui = connections["default"].get_unified_index()
        index = ui.get_index(Dataset)

        with CaptureQueriesContext(connection) as ctx:
            list(index.index_queryset()[:1])

        main_query = ctx.captured_queries[0]["sql"]

        # Should use EXISTS, not DISTINCT
        assert "EXISTS" in main_query, "Expected EXISTS subquery for translation filter"
        assert "SELECT DISTINCT" not in main_query, "Should not use DISTINCT with EXISTS subquery"

    def test_query_count_scales_constantly(self):
        for _ in range(10):
            DatasetFactory()

        ui = connections["default"].get_unified_index()
        index = ui.get_index(Dataset)

        with CaptureQueriesContext(connection) as ctx_3:
            datasets_3 = list(index.index_queryset()[:3])
            with patch("haystack.backends.elasticsearch_backend.ElasticsearchSearchBackend.update"):
                for ds in datasets_3:
                    index.full_prepare(ds)
        count_3 = len(ctx_3.captured_queries)

        with CaptureQueriesContext(connection) as ctx_10:
            datasets_10 = list(index.index_queryset()[:10])
            with patch("haystack.backends.elasticsearch_backend.ElasticsearchSearchBackend.update"):
                for ds in datasets_10:
                    index.full_prepare(ds)
        count_10 = len(ctx_10.captured_queries)

        assert count_10 <= count_3 + 7, (
            f"Query count should scale constantly, got {count_3} for 3 datasets vs {count_10} for 10"
        )


@pytest.mark.django_db(transaction=True)
class TestSignalProcessorTransactionSafety:
    @pytest.mark.haystack
    def test_no_orphan_on_transaction_rollback(self):
        backend = connections["default"].get_backend()

        try:
            with transaction.atomic():
                dataset = DatasetFactory()
                pk = dataset.pk
                raise Exception("Force rollback")
        except Exception:
            pass

        assert not Dataset.objects.filter(pk=pk).exists(), "DB record should not exist after rollback"

        try:
            backend.conn.indices.refresh(index=backend.index_name)
            doc_id = f"vitrina_datasets.dataset.{pk}"
            result = backend.conn.exists(index=backend.index_name, id=doc_id)
        except NotFoundError:
            result = False

        assert result is False, (
            f"Orphaned ES document found for pk={pk}. "
            "The signal processor indexed the document inside a transaction that was rolled back."
        )

    @pytest.mark.haystack
    def test_indexes_after_transaction_commit(self):
        backend = connections["default"].get_backend()

        dataset = DatasetFactory()

        backend.conn.indices.refresh(index=backend.index_name)
        doc_id = f"vitrina_datasets.dataset.{dataset.pk}"
        result = backend.conn.exists(index=backend.index_name, id=doc_id)
        assert result is True, "ES document should exist after a committed save"
