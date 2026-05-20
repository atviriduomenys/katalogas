import pytest

from vitrina.datasets.factories import DatasetFactory
from vitrina.dcat.form_helpers import get_available_dcat_name_prefixes
from vitrina.orgs.factories import OrganizationFactory

pytestmark = pytest.mark.django_db


class TestGetAvailableDcatNamePrefixes:
    def test_returns_parent_name_when_parent_has_name(self):
        organization = OrganizationFactory()
        parent = DatasetFactory(metadata="some/parent")

        result = get_available_dcat_name_prefixes(parent, organization)

        assert result == ["some/parent"]

    def test_returns_org_prefix_and_whitelist_when_parent_has_no_name(self):
        organization = OrganizationFactory()
        parent = DatasetFactory(metadata=False)

        result = get_available_dcat_name_prefixes(parent, organization)

        assert result == [organization.name, "datasets/gov/ivpk/"]

    def test_returns_org_prefix_and_whitelist_when_no_parent(self):
        organization = OrganizationFactory()

        result = get_available_dcat_name_prefixes(None, organization)

        assert result == [organization.name, "datasets/gov/ivpk/"]

    def test_returns_whitelist_only_when_org_has_no_name(self):
        organization = OrganizationFactory(name="")

        result = get_available_dcat_name_prefixes(None, organization)

        assert result == ["datasets/gov/ivpk/"]

    def test_returns_empty_when_org_has_no_name_nor_whitelist(self):
        organization = OrganizationFactory(name="")
        organization.whitelisted_code_names.all().delete()

        result = get_available_dcat_name_prefixes(None, organization)

        assert result == []
