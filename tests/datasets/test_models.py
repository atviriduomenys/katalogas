import pytest

from vitrina.classifiers.factories import ConceptFactory
from vitrina.datasets.factories import DatasetFactory

pytestmark = pytest.mark.django_db


class TestDatasets:
    def test_automatically_assign_information_system_type_if_not_set(self) -> None:
        dataset = DatasetFactory()
        dataset.refresh_from_db()

        assert dataset.information_system_type
        assert dataset.information_system_type.code == "NOT-SET"

    def test_do_not_assign_default_information_system_type_if_it_set(self) -> None:
        concept = ConceptFactory()
        dataset = DatasetFactory(information_system_type=concept)
        dataset.refresh_from_db()

        assert dataset.information_system_type
