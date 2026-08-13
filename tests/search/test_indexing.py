from unittest.mock import patch

from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext

import pytest

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.search import indexing
from vitrina.search.indexing import dataset_index_queryset, index_dataset, rebuild
from vitrina.search.models import DatasetSearchDoc, DatasetSearchFacet, RequestSearchDoc
from vitrina.structure.factories import ModelFactory, PropertyFactory


def _build_catalogue(count):
    for _ in range(count):
        dataset = DatasetFactory()
        DatasetDistributionFactory(dataset=dataset)
        model = ModelFactory(metadata_version__dataset=dataset)
        PropertyFactory(model=model, metadata_version=model.metadata_version)
        RequestFactory(dataset=dataset)
        ProjectFactory(datasets=[dataset])


def _count_queries(work):
    with CaptureQueriesContext(connection) as ctx:
        work()
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestDatasetIndexQuery:
    READ_QUERY_THRESHOLD = 28
    WRITE_QUERIES_PER_DATASET = 12

    def test_reading_the_index_queryset_costs_a_constant_number_of_queries(self):
        _build_catalogue(10)

        reads_3 = _count_queries(lambda: list(dataset_index_queryset()[:3]))
        reads_10 = _count_queries(lambda: list(dataset_index_queryset()[:10]))

        assert reads_10 <= self.READ_QUERY_THRESHOLD
        assert reads_10 <= reads_3 + 2, f"Reads must not grow per dataset: {reads_3} then {reads_10}"

    def test_index_queryset_batches_its_reads(self):
        _build_catalogue(5)

        with CaptureQueriesContext(connection) as ctx:
            list(dataset_index_queryset()[:5])

        in_clause_queries = sum(1 for query in ctx.captured_queries if " IN (" in query["sql"])
        assert in_clause_queries >= 5, "Expected batch queries with IN clauses"

    def test_writing_one_dataset_costs_a_bounded_number_of_queries(self):
        _build_catalogue(10)
        datasets = list(dataset_index_queryset()[:10])

        writes = _count_queries(lambda: [index_dataset(dataset) for dataset in datasets])

        assert writes <= self.WRITE_QUERIES_PER_DATASET * len(datasets)

    def test_index_queryset_excludes_datasets_without_title(self):
        dataset_with_title = DatasetFactory()
        dataset_without_title = DatasetFactory()
        dataset_without_title.translations.all().delete()

        indexed_pks = list(dataset_index_queryset().values_list("pk", flat=True))

        assert dataset_with_title.pk in indexed_pks
        assert dataset_without_title.pk not in indexed_pks

    def test_index_queryset_uses_exists_subquery(self):
        DatasetFactory()

        with CaptureQueriesContext(connection) as ctx:
            list(dataset_index_queryset()[:1])

        main_query = ctx.captured_queries[0]["sql"]
        assert "EXISTS" in main_query, "Expected EXISTS subquery for translation filter"
        assert "SELECT DISTINCT" not in main_query, "Should not use DISTINCT with EXISTS subquery"

    def test_indexing_scales_linearly(self):
        _build_catalogue(10)

        def index(limit):
            return _count_queries(lambda: [index_dataset(d) for d in list(dataset_index_queryset()[:limit])])

        count_3 = index(3)
        count_10 = index(10)

        assert count_10 <= count_3 + self.WRITE_QUERIES_PER_DATASET * 7


@pytest.mark.django_db
class TestSearchDataFollowsTheDatabase:
    def test_save_writes_the_search_row(self):
        dataset = DatasetFactory()

        assert DatasetSearchDoc.objects.filter(pk=dataset.pk).exists()
        assert DatasetSearchFacet.objects.filter(dataset=dataset, field="status").exists()

    def test_delete_removes_the_search_row(self):
        dataset = DatasetFactory()
        pk = dataset.pk
        dataset.delete()

        assert not DatasetSearchDoc.objects.filter(pk=pk).exists()
        assert not DatasetSearchFacet.objects.filter(dataset_id=pk).exists()

    def test_dataset_that_leaves_the_index_loses_its_search_row(self):
        dataset = DatasetFactory()
        assert DatasetSearchDoc.objects.filter(pk=dataset.pk).exists()

        dataset.translations.all().delete()
        dataset.save()

        assert not DatasetSearchDoc.objects.filter(pk=dataset.pk).exists()

    def test_request_save_writes_the_search_row(self):
        request = RequestFactory()

        assert RequestSearchDoc.objects.filter(pk=request.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_rollback_leaves_no_search_row():
    pk = None
    with pytest.raises(Exception, match="Force rollback"):
        with transaction.atomic():
            dataset = DatasetFactory()
            pk = dataset.pk
            raise Exception("Force rollback")

    assert pk is not None
    assert not Dataset.objects.filter(pk=pk).exists()
    assert not DatasetSearchDoc.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_rebuild_indexes_every_dataset_and_request():
    for _ in range(3):
        DatasetFactory()
    RequestFactory()

    DatasetSearchDoc.objects.all().delete()
    RequestSearchDoc.objects.all().delete()

    datasets, requests = rebuild()

    assert datasets == DatasetSearchDoc.objects.count()
    assert requests == RequestSearchDoc.objects.count()
    assert datasets >= 3
    assert requests >= 1


@pytest.mark.django_db
def test_rebuild_drops_the_rows_of_a_dataset_that_left_the_index():
    stays = DatasetFactory()
    leaves = DatasetFactory()
    assert DatasetSearchDoc.objects.filter(pk=leaves.pk).exists()

    leaves.translations.all().delete()

    rebuild()

    assert DatasetSearchDoc.objects.filter(pk=stays.pk).exists()
    assert not DatasetSearchDoc.objects.filter(pk=leaves.pk).exists()
    assert not DatasetSearchFacet.objects.filter(dataset_id=leaves.pk).exists()


@pytest.mark.django_db
def test_rebuild_keeps_every_row_readable_while_it_runs():
    for _ in range(3):
        DatasetFactory()
    before = set(DatasetSearchDoc.objects.values_list("pk", flat=True))

    seen = []
    original = indexing._write_dataset

    def record_then_write(dataset):
        seen.append(set(DatasetSearchDoc.objects.values_list("pk", flat=True)))
        return original(dataset)

    with patch.object(indexing, "_write_dataset", record_then_write):
        rebuild()

    assert seen, "the rebuild wrote nothing"
    for visible in seen:
        assert before <= visible, "a row went missing part way through the rebuild"
