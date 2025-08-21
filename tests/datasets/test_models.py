import pytest

from vitrina.classifiers.factories import ConceptFactory
from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import DCATResourceSubclass

pytestmark = pytest.mark.django_db


class TestDatasets:
    @pytest.mark.parametrize(
        "field_name",
        [
            "information_system_type",
            "information_system_importance",
        ],
    )
    def test_automatically_assign_information_system_mandatory_fields_if_not_set(self, field_name):
        dataset = DatasetFactory()
        dataset.refresh_from_db()

        value = getattr(dataset, field_name)
        assert value is not None
        assert value.code == "NOT-SET"

    @pytest.mark.parametrize(
        "field_name",
        [
            "information_system_type",
            "information_system_importance",
        ],
    )
    def test_do_not_assign_default_information_system_fields_if_it_set(self, field_name):
        concept = ConceptFactory()
        dataset = DatasetFactory(**{field_name: concept})
        dataset.refresh_from_db()

        value = getattr(dataset, field_name)
        assert value == concept



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
