from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.helpers import get_name_prefixes, match_name_prefix
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory, WhitelistedCodeNameFactory
from vitrina.orgs.models import WhitelistedCodeName, Representative
import pytest

pytestmark = pytest.mark.django_db


class TestGetNamePrefixes:
    def test_prefixes_comes_from_organization(self):
        organization = OrganizationFactory(name="datasets/gov/test")
        WhitelistedCodeName.objects.filter(organization=organization).delete()
        WhitelistedCodeNameFactory(organization=organization, code_name="test/codename/")

        main, whitelisted = get_name_prefixes(organization, None)

        assert main == "datasets/gov/test"
        assert whitelisted == ["test/codename/"]

    def test_prefixes_comes_from_dataset_organization_if_organization_is_none(self):
        organization = OrganizationFactory(name="datasets/gov/test")
        WhitelistedCodeName.objects.filter(organization=organization).delete()
        WhitelistedCodeNameFactory(organization=organization, code_name="test/codename/")
        dataset = DatasetFactory(title="testt", organization=organization)

        main, whitelisted = get_name_prefixes(None, dataset)

        assert main == "datasets/gov/test"
        assert whitelisted == ["test/codename/"]

    def test_main_prefix_takes_precedence_from_organization_over_dataset_organization(self):
        direct_organization = OrganizationFactory(name="datasets/gov/test1")
        WhitelistedCodeName.objects.filter(organization=direct_organization).delete()
        WhitelistedCodeNameFactory(organization=direct_organization, code_name="test/codename/1/")
        dataset_organization = OrganizationFactory(name="datasets/org/test2")
        dataset = DatasetFactory(title="testt", organization=dataset_organization)

        main, whitelisted = get_name_prefixes(direct_organization, dataset)

        assert main == "datasets/gov/test1"
        assert whitelisted == ["test/codename/1/"]

    def test_prefixes_empty_if_no_organization_or_on_dataset_given(self):
        main, whitelisted = get_name_prefixes(None, None)

        assert main == ""
        assert whitelisted == []

    def test_prefixes_empty_if_organization_has_no_name_and_no_whitelisted_codenames(self):
        organization = OrganizationFactory(name="")
        WhitelistedCodeName.objects.filter(organization=organization).delete()
        dataset = DatasetFactory(title="testt", organization=organization)
        main, whitelisted = get_name_prefixes(organization, dataset)

        assert main == ""
        assert whitelisted == []

    def test_prefixes_return_multiple_whitelisted_prefixes(self):
        organization = OrganizationFactory(name="datasets/gov/test")
        WhitelistedCodeName.objects.filter(organization=organization).delete()
        WhitelistedCodeNameFactory(organization=organization, code_name="test/codename/1/")
        WhitelistedCodeNameFactory(organization=organization, code_name="test/codename/2/")

        main, whitelisted = get_name_prefixes(organization, None)

        assert main == "datasets/gov/test"
        assert set(whitelisted) == {"test/codename/1/", "test/codename/2/"}

    def test_prefixes_return_whitelisted_prefix_from_open_data_publisher_organization_names(self):
        organization = OrganizationFactory(name="datasets/gov/publisher")
        WhitelistedCodeName.objects.filter(organization=organization).delete()

        representative_organization = OrganizationFactory(name="datasets/gov/test/1")
        WhitelistedCodeName.objects.filter(organization=representative_organization).delete()
        WhitelistedCodeNameFactory(organization=representative_organization, code_name="representative/codename/")
        RepresentativeFactory(
            organization=organization,
            role=Representative.OPEN_DATA_PUBLISHER,
            content_type=ContentType.objects.get_for_model(representative_organization),
            object_id=representative_organization.pk,
        )

        dataset_organization = OrganizationFactory(name="datasets/gov/test/2")
        WhitelistedCodeName.objects.filter(organization=dataset_organization).delete()
        WhitelistedCodeNameFactory(organization=dataset_organization, code_name="dataset/codename/")
        dataset = DatasetFactory(title="testt", organization=dataset_organization)
        RepresentativeFactory(
            organization=organization,
            role=Representative.OPEN_DATA_PUBLISHER,
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
        )

        main, whitelisted = get_name_prefixes(organization)

        assert main == "datasets/gov/publisher"
        assert set(whitelisted) == {"datasets/gov/test/1", "datasets/gov/test/2"}


class TestMatchNamePrefix:
    @pytest.mark.parametrize(
        "name, all_prefixes, result",
        [
            ("datasets/gov/test/", ["datasets/gov/test/", "datasets/gov/"], "datasets/gov/test/"),
            ("datasets/gov/test/", ["datasets/gov/", "datasets/gov/test/"], "datasets/gov/"),
            ("datasets/gov/test/", [], None),
            ("datasets/gov/test/", ["datasets/gov/test/one/", "datasets/gov/test/two/"], None),
            (None, ["datasets/gov/test/", "datasets/gov/"], None),
        ],
    )
    def test_match_prefix(self, name: str | None, all_prefixes: list[str], result: str | None):
        assert match_name_prefix(name, all_prefixes) == result
