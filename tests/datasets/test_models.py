import pytest

from vitrina.classifiers.factories import ConceptFactory
from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import DCATResourceSubclass

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


class TestDCATResourceSubclass:
    @pytest.mark.parametrize(
        "name, result",
        [
            (DCATResourceSubclass.SERIES, False),
            (DCATResourceSubclass.SERVICE, False),
            (DCATResourceSubclass.INFORMATION_SYSTEM, True),
        ],
    )
    def test_is_information_system(self, name: str, result: bool) -> None:
        subclass = DCATResourceSubclassFactory(name=name)
        assert subclass.is_information_system is result
