from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.helpers import get_name_prefixes
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import WhitelistedCodeName, Representative
import pytest


@pytest.mark.django_db
def test_get_name_prefixes_matches_main_prefix():
    org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=org).delete()
    matched, main, whitelisted = get_name_prefixes("datasets/gov/test/dataset", org)
    assert matched == "datasets/gov/test"
    assert main == "datasets/gov/test"
    assert whitelisted == []


@pytest.mark.django_db
def test_get_name_prefixes_matches_whitelisted_prefix():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=["datasets/org/test"])
    WhitelistedCodeName.objects.filter(organization=org).exclude(code_name="datasets/org/test").delete()
    matched, main, whitelisted = get_name_prefixes("datasets/org/test/dataset", org)
    assert matched == "datasets/org/test"


@pytest.mark.django_db
def test_get_name_prefixes_matches_no_prefix():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=["datasets/org/test"])
    WhitelistedCodeName.objects.filter(organization=org).exclude(code_name="datasets/org/test").delete()
    matched, main, whitelisted = get_name_prefixes("datasets/other/test/dataset", org)
    assert matched is None


@pytest.mark.django_db
def test_get_name_prefixes_resolves_org_from_dataset_instance():
    org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=org).delete()
    dataset = DatasetFactory(title="testt", organization=org)
    matched, main, whitelisted = get_name_prefixes("datasets/gov/test/dataset", None, dataset)
    assert matched == "datasets/gov/test"
    assert main == "datasets/gov/test"


@pytest.mark.django_db
def test_get_name_prefixes_organization_takes_precedence_over_dataset():
    direct_org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=direct_org).delete()
    dataset_org = OrganizationFactory(name="datasets/org/test")
    dataset = DatasetFactory(title="testt", organization=dataset_org)
    matched, main, _ = get_name_prefixes("datasets/gov/test/dataset", direct_org, dataset)
    assert main == "datasets/gov/test"


@pytest.mark.django_db
def test_get_name_prefixes_returns_all_whitelisted_names():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=["datasets/org/test", "datasets/org/other"])
    WhitelistedCodeName.objects.filter(organization=org).exclude(
        code_name__in=["datasets/org/test", "datasets/org/other"]
    ).delete()
    _, _, whitelisted = get_name_prefixes("datasets/gov/test/dataset", org)
    assert set(whitelisted) == {"datasets/org/test", "datasets/org/other"}


@pytest.mark.django_db
def test_get_name_prefixes_empty_whitelisted_names():
    org = OrganizationFactory(name="datasets/gov/test", whitelisted_names=[])
    WhitelistedCodeName.objects.filter(organization=org).delete()
    _, _, whitelisted = get_name_prefixes("datasets/gov/test/dataset", org)
    assert whitelisted == []


def test_get_name_prefixes_no_organization():
    matched, main, whitelisted = get_name_prefixes("datasets/gov/test/dataset", None, None)
    assert matched is None
    assert main == ""
    assert whitelisted == []


@pytest.mark.django_db
def test_get_name_prefixes_empty_name():
    org = OrganizationFactory(name="datasets/gov/test")
    WhitelistedCodeName.objects.filter(organization=org).delete()
    matched, main, whitelisted = get_name_prefixes("", org)
    assert matched is None
    assert main == "datasets/gov/test"


@pytest.mark.django_db
def test_get_name_prefixes_with_publisher_role():
    publisher = OrganizationFactory(name="datasets/gov/publisher", whitelisted_names=[])
    org = OrganizationFactory(name="datasets/gov/test")
    RepresentativeFactory(
        organization=publisher,
        role=Representative.OPEN_DATA_PUBLISHER,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
    )
    _, _, whitelisted = get_name_prefixes("datasets/gov/test", publisher)
    assert "datasets/gov/test" in whitelisted
