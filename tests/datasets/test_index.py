import pytest
from unittest.mock import patch

from django.test.utils import CaptureQueriesContext

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory, OrganizationFactory
from vitrina.orgs.models import Representative
from vitrina.requests.factories import RequestObjectFactory, RequestFactory
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat, UapiFormat
from vitrina.users.factories import UserFactory


@pytest.fixture
def mock_index_update():
    with patch("vitrina.datasets.search_indexes.CustomSignalProcessor._update_dataset_indexes") as mock:
        yield mock


@pytest.fixture
def mock_request_index_update():
    with patch("vitrina.datasets.search_indexes.CustomSignalProcessor._update_related_request_indexes") as mock:
        yield mock


@pytest.fixture
def mock_distribution_index_update():
    with patch("vitrina.datasets.search_indexes.CustomSignalProcessor._update_single_dataset") as mock:
        yield mock


@pytest.mark.django_db
class TestRepresentativeIndexUpdates:
    def test_representative_added_to_dataset_updates_index(self, mock_index_update):
        dataset = DatasetFactory()

        RepresentativeFactory(content_object=dataset, user=UserFactory())

        # Check that the update was called with the dataset
        mock_index_update.assert_called_once()
        updated_datasets = list(mock_index_update.call_args[0][0])
        assert dataset in updated_datasets

    def test_representative_deleted_from_dataset_updates_index(self, mock_index_update):
        dataset = DatasetFactory()
        rep = RepresentativeFactory(content_object=dataset, user=UserFactory())

        mock_index_update.reset_mock()
        rep.delete()

        mock_index_update.assert_called_once()
        updated_datasets = list(mock_index_update.call_args[0][0])
        assert dataset in updated_datasets

    def test_representative_changed_updates_index(self, mock_index_update):
        dataset = DatasetFactory()
        rep = RepresentativeFactory(content_object=dataset, user=UserFactory())

        mock_index_update.reset_mock()
        rep.role = Representative.COORDINATOR
        rep.save()

        mock_index_update.assert_called_once()
        updated_datasets = list(mock_index_update.call_args[0][0])
        assert dataset in updated_datasets

    def test_representative_added_to_organization_updates_all_org_datasets(self, mock_index_update):
        org = OrganizationFactory()
        dataset1 = DatasetFactory(organization=org)
        dataset2 = DatasetFactory(organization=org)
        other_dataset = DatasetFactory()  # Different org

        RepresentativeFactory(content_object=org, user=UserFactory())

        updated_datasets = list(mock_index_update.call_args[0][0])
        assert dataset1 in updated_datasets
        assert dataset2 in updated_datasets
        assert other_dataset not in updated_datasets

    def test_representative_with_organization_field_updates_org_datasets(self, mock_index_update):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        other_org = OrganizationFactory()

        RepresentativeFactory(content_object=other_org, organization=org, user=UserFactory())

        updated_datasets = list(mock_index_update.call_args[0][0])
        assert dataset in updated_datasets

    def test_representative_updates_dataset_descendants(self, mock_index_update):
        parent_dataset = DatasetFactory()
        child_dataset = DatasetFactory()
        child_dataset.move(parent_dataset, "sorted-child")

        mock_index_update.reset_mock()

        RepresentativeFactory(content_object=parent_dataset, user=UserFactory())

        updated_datasets = list(mock_index_update.call_args[0][0])
        assert parent_dataset in updated_datasets
        assert child_dataset in updated_datasets

    def test_representative_updates_organization_descendant_datasets(self, mock_index_update):
        parent_org = OrganizationFactory()
        child_org = OrganizationFactory()
        child_org.move(parent_org, "sorted-child")

        parent_dataset = DatasetFactory(organization=parent_org)
        child_dataset = DatasetFactory(organization=child_org)

        mock_index_update.reset_mock()

        RepresentativeFactory(content_object=parent_org, user=UserFactory())

        updated_datasets = list(mock_index_update.call_args[0][0])
        assert parent_dataset in updated_datasets
        assert child_dataset in updated_datasets

    def test_representative_deleted_dataset_doesnt_crash(self, mock_index_update):
        dataset = DatasetFactory()
        rep = RepresentativeFactory(content_object=dataset, user=UserFactory())

        dataset.delete()

        mock_index_update.reset_mock()
        rep.delete()

        mock_index_update.assert_called_once()

    def test_multiple_representatives_single_dataset_updates_once(self, mock_index_update):
        dataset = DatasetFactory()

        RepresentativeFactory(content_object=dataset, user=UserFactory())
        mock_index_update.reset_mock()
        RepresentativeFactory(content_object=dataset, user=UserFactory())

        updated_datasets = list(mock_index_update.call_args[0][0])
        assert updated_datasets.count(dataset) == 1

    def test_representative_org_with_no_descendants_works(self, mock_index_update):
        org = OrganizationFactory()  # No children
        dataset = DatasetFactory(organization=org)

        mock_index_update.reset_mock()
        RepresentativeFactory(content_object=org, user=UserFactory())

        updated_datasets = list(mock_index_update.call_args[0][0])
        assert dataset in updated_datasets
        assert len(updated_datasets) == 1


@pytest.mark.django_db
class TestDatasetDistributionIndexUpdates:
    def test_distribution_created_updates_dataset_index(self, mock_distribution_index_update):
        dataset = DatasetFactory()

        mock_distribution_index_update.reset_mock()

        DatasetDistributionFactory(dataset=dataset)

        mock_distribution_index_update.assert_called_once()

    def test_distribution_format_changed_updates_dataset_index(self, mock_distribution_index_update):
        dataset = DatasetFactory()
        api_format = UapiFormat()
        csv_format = FileFormat(title="CSV", extension="CSV")

        distribution = DatasetDistributionFactory(dataset=dataset, format=api_format)

        mock_distribution_index_update.reset_mock()

        # Change format from API to CSV
        distribution.format = csv_format
        distribution.save()

        mock_distribution_index_update.assert_called_once()

    def test_distribution_deleted_updates_dataset_index(self, mock_distribution_index_update):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset)

        mock_distribution_index_update.reset_mock()
        distribution.delete()

        mock_distribution_index_update.assert_called_once()

    def test_multiple_distributions_same_dataset_updates_once_per_change(self, mock_distribution_index_update):
        dataset = DatasetFactory()

        dist1 = DatasetDistributionFactory(dataset=dataset)
        mock_distribution_index_update.reset_mock()

        DatasetDistributionFactory(dataset=dataset)

        assert mock_distribution_index_update.call_count == 1

        mock_distribution_index_update.reset_mock()
        dist1.set_current_language("en")
        dist1.title = "Updated title"
        dist1.save()

        assert mock_distribution_index_update.call_count == 1

    def test_distribution_dataset_deleted_doesnt_crash(self, mock_distribution_index_update):
        dataset = DatasetFactory()
        DatasetDistributionFactory(dataset=dataset)

        dataset.delete()

        mock_distribution_index_update.reset_mock()

    def test_distribution_multiple_field_changes_single_update(self, mock_distribution_index_update):
        dataset = DatasetFactory()
        csv_format = FileFormat(title="CSV", extension="CSV")
        json_format = FileFormat(title="JSON", extension="JSON")

        distribution = DatasetDistributionFactory(dataset=dataset, format=csv_format)

        mock_distribution_index_update.reset_mock()

        distribution.format = json_format
        distribution.set_current_language("en")
        distribution.title = "New title"
        distribution.description = "New description"
        distribution.save()

        assert mock_distribution_index_update.call_count == 1

    def test_uapi_format_distribution_updates_dataset_index(self, mock_distribution_index_update):
        dataset = DatasetFactory()

        mock_distribution_index_update.reset_mock()

        distribution = DatasetDistributionFactory(dataset=dataset, uapi_format=True)

        mock_distribution_index_update.assert_called_once()

        assert distribution.format.extension == "UAPI"


@pytest.mark.django_db
class TestDatasetRequestIndexUpdates:
    def test_dataset_save_updates_related_request_indexes(self, mock_request_index_update):
        dataset = DatasetFactory()
        request = RequestFactory()
        RequestObjectFactory(content_object=dataset, request=request)

        mock_request_index_update.reset_mock()
        dataset.set_current_language("lt")
        dataset.title = "Updated Title"
        dataset.save()

        # Should update the request index
        mock_request_index_update.assert_called()

    def test_dataset_save_with_multiple_requests_updates_all(self, mock_request_index_update):
        dataset = DatasetFactory()
        request1 = RequestFactory()
        request2 = RequestFactory()
        RequestObjectFactory(content_object=dataset, request=request1)
        RequestObjectFactory(content_object=dataset, request=request2)

        mock_request_index_update.reset_mock()
        dataset.save()

        assert mock_request_index_update.call_count == 1

    def test_dataset_save_without_requests_doesnt_crash(self, mock_request_index_update):
        dataset = DatasetFactory()
        mock_request_index_update.reset_mock()
        dataset.save()
        # No crash = success

@pytest.mark.django_db
class TestDatasetIndexQuery:

    def test_dataset_index_query_count(self):
        from django.db import connection
        from haystack import connections

        DatasetFactory()
        DatasetFactory()
        DatasetFactory()
        DatasetFactory()
        DatasetFactory()
        datasets = [ds for ds in Dataset.objects.order_by("-created")[:5]]
        ui = connections["default"].get_unified_index()
        index = ui.get_index(Dataset)
        docs = []
        with CaptureQueriesContext(connection) as ctx:
            with patch("haystack.backends.elasticsearch_backend.ElasticsearchSearchBackend.update", autospec=True):
                for ds in datasets:
                    docs.append(index.full_prepare(ds))

            assert len(ctx.captured_queries) <= 10, f"Too many queries: {len(ctx.captured_queries)}"
