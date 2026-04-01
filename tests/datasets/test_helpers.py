from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.helpers import validate_name_prefix
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import WhitelistedCodeName
import pytest


@pytest.mark.django_db
def test_validate_name_prefix_matches_main_prefix():
    org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=org).delete()
    matched, main, whitelisted = validate_name_prefix("datasets/gov/test/dataset", org)
    assert matched == "datasets/gov/test"
    assert main == "datasets/gov/test"
    assert whitelisted == []


@pytest.mark.django_db
def test_validate_name_prefix_matches_whitelisted_prefix():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=["datasets/org/test"])
    WhitelistedCodeName.objects.filter(organization=org).exclude(code_name="datasets/org/test").delete()
    matched, main, whitelisted = validate_name_prefix("datasets/org/test/dataset", org)
    assert matched == "datasets/org/test"


@pytest.mark.django_db
def test_validate_name_prefix_matches_no_prefix():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=["datasets/org/test"])
    WhitelistedCodeName.objects.filter(organization=org).exclude(code_name="datasets/org/test").delete()
    matched, main, whitelisted = validate_name_prefix("datasets/other/test/dataset", org)
    assert matched is None


@pytest.mark.django_db
def test_validate_name_prefix_resolves_org_from_dataset_instance():
    org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=org).delete()
    dataset = DatasetFactory(title="testt", organization=org)
    matched, main, whitelisted = validate_name_prefix("datasets/gov/test/dataset", None, dataset)
    assert matched == "datasets/gov/test"
    assert main == "datasets/gov/test"


@pytest.mark.django_db
def test_validate_name_prefix_organization_takes_precedence_over_dataset():
    direct_org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=direct_org).delete()
    dataset_org = OrganizationFactory(name="datasets/org/test")
    dataset = DatasetFactory(title="testt", organization=dataset_org)
    matched, main, _ = validate_name_prefix("datasets/gov/test/dataset", direct_org, dataset)
    assert main == "datasets/gov/test"


@pytest.mark.django_db
def test_validate_name_prefix_returns_all_whitelisted_names():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=["datasets/org/test", "datasets/org/other"])
    WhitelistedCodeName.objects.filter(organization=org).exclude(
        code_name__in=["datasets/org/test", "datasets/org/other"]
    ).delete()
    _, _, whitelisted = validate_name_prefix("datasets/gov/test/dataset", org)
    assert set(whitelisted) == {"datasets/org/test", "datasets/org/other"}


@pytest.mark.django_db
def test_validate_name_prefix_empty_whitelisted_names():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=[])
    WhitelistedCodeName.objects.filter(organization=org).delete()
    _, _, whitelisted = validate_name_prefix("datasets/gov/test/dataset", org)
    assert whitelisted == []


def test_validate_name_prefix_no_organization():
    matched, main, whitelisted = validate_name_prefix("datasets/gov/test/dataset", None, None)
    assert matched is None
    assert main == ""
    assert whitelisted == []


@pytest.mark.django_db
def test_validate_name_prefix_empty_name():
    org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=org).delete()
    matched, main, whitelisted = validate_name_prefix("", org)
    assert matched is None
    assert main == "datasets/gov/test"
