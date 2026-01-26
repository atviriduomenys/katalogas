from datetime import datetime

import pytest
import pytz
from django.conf import settings


from vitrina.classifiers.factories import ConceptFactory
from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import DCATResourceSubclass, Dataset
from vitrina.orgs.factories import OrganizationFactory

pytestmark = pytest.mark.django_db


class TestDatasets:
    def test_translations_default_language(self):
        dataset = DatasetFactory()
        default_language = dataset.get_current_language()
        assert default_language == "lt"

    def test_language_changes(self):
        dataset = DatasetFactory()
        dataset.set_current_language("en")
        current = dataset.get_current_language()
        assert current == "en"

    def test_public_manager_filtering(self):
        organization = OrganizationFactory(slug="org", kind="gov")

        DatasetFactory(is_public=False, organization=organization)
        DatasetFactory(
            deleted=True,
            deleted_on=pytz.timezone(settings.TIME_ZONE).localize(datetime.now()),
            organization=organization,
        )
        DatasetFactory(deleted=True, deleted_on=None, organization=organization)
        DatasetFactory(deleted=None, deleted_on=None, organization=organization)
        DatasetFactory(organization=organization)

        public_datasets = Dataset.public.all().exclude(id=1)
        assert public_datasets.count() == 2

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

    @pytest.mark.parametrize(
        "name, result",
        [
            (DCATResourceSubclass.SERIES, False),
            (DCATResourceSubclass.SERVICE, False),
            (DCATResourceSubclass.DATASET, True),
        ],
    )
    def test_is_dataset(self, name: str, result: bool) -> None:
        subclass = DCATResourceSubclassFactory(name=name)
        assert subclass.is_dataset is result

    @pytest.mark.parametrize(
        "name, result",
        [
            (DCATResourceSubclass.SERIES, False),
            (DCATResourceSubclass.SERVICE, False),
            (DCATResourceSubclass.CATALOG, True),
        ],
    )
    def test_is_catalog(self, name: str, result: bool) -> None:
        subclass = DCATResourceSubclassFactory(name=name)
        assert subclass.is_catalog is result
