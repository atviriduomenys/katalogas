import pytest
from django.core.exceptions import ValidationError

from vitrina.orgs.factories import OrganizationFactory, WhitelistedCodeNameFactory
from vitrina.orgs.helpers import generate_dataset_prefix, validate_global_uniqueness
from vitrina.orgs.models import Organization


@pytest.mark.parametrize(
    "name, kind, expected",
    [
        ("VSSA", Organization.GOV, "datasets/gov/vssa/"),
        ("Test Org", Organization.COM, "datasets/org/test-org/"),
        ("My_Company", Organization.ORG, "datasets/org/my-company/"),
    ],
)
def test_generate_dataset_prefix(name: str, kind: Organization.ORGANIZATION_KINDS, expected: str) -> None:
    assert generate_dataset_prefix(name, kind) == expected


@pytest.mark.django_db
def test_validate_global_uniqueness_organization_name():
    org = OrganizationFactory(name="org")
    with pytest.raises(ValidationError):
        validate_global_uniqueness("org")
    validate_global_uniqueness("new_org")
    validate_global_uniqueness("org", instance=org)


@pytest.mark.django_db
def test_validate_global_uniqueness_whitelisted_code():
    code = WhitelistedCodeNameFactory(code_name="datasets/gov/test/")
    with pytest.raises(ValidationError):
        validate_global_uniqueness("datasets/gov/test/")
    validate_global_uniqueness("datasets/org/test/")
    validate_global_uniqueness("datasets/org/test/", instance=code)
