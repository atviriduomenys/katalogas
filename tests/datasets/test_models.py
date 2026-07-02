from datetime import datetime

import json

import pytest
import pytz
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import escape

from vitrina.classifiers.factories import ConceptFactory
from vitrina.datasets.factories import (
    DatasetFactory,
    DCATResourceSubclassFactory,
    DatasetServiceFactory,
    ContactFactory,
)
from vitrina.datasets import ContactKind
from vitrina.datasets.models import DCATResourceSubclass, Dataset, Contact
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.structure.factories import VersionFactory, ModelFactory, MetadataFactory
from vitrina.structure.models import VersionStatus, Model as StructureModel, MetadataVersion
from vitrina.users.factories import UserFactory
from vitrina.uapi.factories import AgentFactory, AgentEnvironmentFactory
from vitrina.uapi.models import Environment


XSS_PAYLOAD = "<script>alert('xss')</script>"

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

    def test_get_effective_user_role_via_organization_returns_none_when_user_has_no_org_memberships(self):
        dataset = DatasetFactory()
        user = UserFactory()
        assert dataset.get_effective_user_role_via_organization(user) is None

    def test_get_effective_user_role_via_organization_returns_none_when_user_org_is_not_a_representative(self):
        dataset = DatasetFactory()
        user = UserFactory()
        unrelated_org = OrganizationFactory()
        org_ct = ContentType.objects.get_for_model(unrelated_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=unrelated_org.pk,
            user=user,
            organization=None,
        )
        assert dataset.get_effective_user_role_via_organization(user) is None

    def test_get_effective_user_role_via_organization_returns_none_when_user_belongs_to_multiple_orgs_but_none_are_representatives(
        self,
    ):
        dataset = DatasetFactory()
        user = UserFactory()

        for _ in range(3):
            org = OrganizationFactory()
            org_ct = ContentType.objects.get_for_model(org)
            RepresentativeFactory(
                content_type=org_ct,
                object_id=org.pk,
                user=user,
                organization=None,
            )

        assert dataset.get_effective_user_role_via_organization(user) is None

    def test_get_effective_user_role_via_organization_returns_role_when_user_org_represents_dataset(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_organization(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_organization_returns_role_when_user_org_represents_dataset_organization(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset.organization),
            object_id=dataset.organization.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_organization(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_organization_returns_role_when_user_org_represents_ancestor_dataset(self):
        parent = DatasetFactory()
        child = DatasetFactory()
        child.move(parent, pos="sorted-child")
        child.refresh_from_db()

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent),
            object_id=parent.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert child.get_effective_user_role_via_organization(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_organization_returns_role_when_user_org_represents_ancestor_organization(self):
        parent = DatasetFactory()
        child = DatasetFactory(organization=parent.organization)
        child.move(parent, pos="sorted-child")
        child.refresh_from_db()

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent.organization),
            object_id=parent.organization.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert child.get_effective_user_role_via_organization(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_organization_organization_role_lower_than_user(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_organization(user) == Representative.OPEN_DATA_MANAGER

    @pytest.mark.parametrize(
        "role",
        [
            Representative.RESOURCE_MANAGER,
            Representative.OPEN_DATA_MANAGER,
        ],
    )
    def test_get_effective_user_role_via_organization_returns_correct_role_for_all_role_types(self, role):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=role,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=role,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_organization(user) == role

    def test_get_effective_user_role_via_organization_open_data_manager_org_restricts_resource_manager_user(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_organization(user) == Representative.OPEN_DATA_MANAGER

    def test_get_effective_user_role_via_organization_resource_manager_org_preserves_open_data_manager_user(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.OPEN_DATA_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_organization(user) == Representative.OPEN_DATA_MANAGER

    def test_data_service_get_endpoint_urls_without_agent(self):
        endpoint_url = "http://www.test.com"
        data_service = DatasetServiceFactory(endpoint_url=endpoint_url)

        endpoint_urls = data_service.get_endpoint_urls()
        assert len(endpoint_urls) == 1
        url_name, url = endpoint_urls[0]
        assert not url_name
        assert url == endpoint_url

    def test_get_endpoint_urls_with_agent(self):
        endpoint_url = "http://www.endpoint.com"
        gate_url = "http://www.gate.com"
        agent = AgentFactory()
        env_testing = AgentEnvironmentFactory(agent=agent, agent_address=endpoint_url, environment=Environment.TESTING)
        env_development = AgentEnvironmentFactory(
            agent=agent, agent_address=endpoint_url, api_gate_server_url=gate_url, environment=Environment.DEVELOPMENT
        )
        data_service = DatasetServiceFactory(agent=agent)

        endpoint_urls = data_service.get_endpoint_urls()
        assert len(endpoint_urls) == 2
        test_url_name, test_url = endpoint_urls[0]
        dev_url_name, dev_url = endpoint_urls[1]
        assert test_url_name == env_testing.get_environment_display()
        assert test_url == env_testing.agent_address
        assert dev_url_name == env_development.get_environment_display()
        assert dev_url == env_development.api_gate_server_url

    def test_get_endpoint_description_without_agent(self):
        url = "http://www.test.com"
        data_service = DatasetServiceFactory(endpoint_description=url)

        description_url = data_service.get_endpoint_description()

        assert description_url == url

    def test_get_endpoint_description_with_agent(self):
        agent = AgentFactory()
        data_service = DatasetServiceFactory(agent=agent)

        endpoint_description = data_service.get_endpoint_description()

        assert endpoint_description == reverse(
            "dataset-structure-export-openapi", args=[data_service.pk, data_service.latest_version().pk]
        )


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


class TestContact:
    def test_str_individual(self):
        user = UserFactory(first_name="Jonas", last_name="Jonaitis")
        org = OrganizationFactory()
        contact = ContactFactory(
            kind=ContactKind.INDIVIDUAL,
            position="Manager",
            organization=org,
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
        )
        assert str(contact) == "Jonas Jonaitis (Manager)"

    def test_str_org(self):
        linked_org = OrganizationFactory(title="My Org")
        org = OrganizationFactory()
        contact = ContactFactory(
            kind=ContactKind.ORG,
            organization=org,
            content_type=ContentType.objects.get_for_model(linked_org),
            object_id=linked_org.pk,
        )
        assert str(contact) == "My Org"

    def test_str_unregistered(self):
        org = OrganizationFactory()
        contact = ContactFactory(
            kind=ContactKind.UNREGISTERED,
            contact_name="Petras Petraitis",
            position="Analyst",
            organization=org,
            content_type=None,
            object_id=None,
        )
        assert str(contact) == "Petras Petraitis (Analyst)"

    def test_str_service(self):
        org = OrganizationFactory()
        contact = ContactFactory(
            kind=ContactKind.SERVICE,
            contact_name="Help Desk",
            organization=org,
            content_type=None,
            object_id=None,
        )
        assert str(contact) == "Help Desk"

    def test_get_email_returns_own_email_when_set(self):
        contact = ContactFactory(email="direct@example.com")
        assert contact.get_email() == "direct@example.com"

    def test_get_email_falls_back_to_content_object_email(self):
        user = UserFactory(email="user@example.com")
        org = OrganizationFactory()
        contact = ContactFactory(
            email="",
            organization=org,
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
        )
        assert contact.get_email() == "user@example.com"

    def test_get_email_returns_empty_string_when_no_email(self):
        org = OrganizationFactory()
        contact = ContactFactory(
            kind=ContactKind.UNREGISTERED,
            email="",
            organization=org,
            content_type=None,
            object_id=None,
        )
        assert contact.get_email() == ""

    def test_kind_for_object_org(self):
        org = OrganizationFactory()
        assert Contact.kind_for_object(org) == ContactKind.ORG

    def test_kind_for_object_user(self):
        user = UserFactory()
        assert Contact.kind_for_object(user) == ContactKind.INDIVIDUAL

    def test_kind_for_object_other(self):
        assert Contact.kind_for_object(object()) == ContactKind.UNREGISTERED

    def test_get_type_returns_kind_display(self):
        contact = ContactFactory(kind=ContactKind.SERVICE)
        assert contact.get_type() == contact.get_kind_display()

    def test_is_service_kind_true(self):
        contact = ContactFactory(kind=ContactKind.SERVICE)
        assert contact.is_service_kind() is True

    def test_is_service_kind_false(self):
        contact = ContactFactory(kind=ContactKind.UNREGISTERED)
        assert contact.is_service_kind() is False


@pytest.mark.django_db
class TestDatasetGetMetadataObjectsForVersionXSS:
    def test_model_name_is_escaped_in_label(self):
        version = VersionFactory(status=VersionStatus.DRAFT)
        dataset = version.dataset
        struct_model = ModelFactory(metadata_version=version, dataset=dataset)
        MetadataFactory(
            dataset=dataset,
            metadata_version=version,
            draft=True,
            name=XSS_PAYLOAD,
            content_type=ContentType.objects.get_for_model(StructureModel),
            object_id=struct_model.pk,
        )

        result = dataset.get_metadata_objects_for_version(version)
        labels = "".join(str(label) for _, label in result)

        assert XSS_PAYLOAD not in labels
        assert escape(XSS_PAYLOAD) in labels

    def test_metadata_name_diff_is_escaped_in_label(self):
        version = VersionFactory(status=VersionStatus.DRAFT)
        dataset = version.dataset
        struct_model = ModelFactory(metadata_version=version, dataset=dataset)
        metadata = MetadataFactory(
            dataset=dataset,
            metadata_version=version,
            draft=True,
            name=XSS_PAYLOAD,
            content_type=ContentType.objects.get_for_model(StructureModel),
            object_id=struct_model.pk,
        )
        old_version = VersionFactory(dataset=dataset)
        MetadataVersion.objects.create(
            metadata=metadata,
            version=old_version,
            name="safe_old_name",
        )

        result = dataset.get_metadata_objects_for_version(version)
        labels = "".join(str(label) for _, label in result)

        assert XSS_PAYLOAD not in labels
        assert escape(XSS_PAYLOAD) in labels


class TestDatasetGetJsonLd:
    def test_json_ld_escapes_script_breakout(self):
        title = "Test </script><script>alert('xss')</script>"
        dataset = DatasetFactory(title=title)

        json_ld = dataset.get_json_ld()

        assert "</script>" not in json_ld
        assert "<script>" not in json_ld
        assert json.loads(json_ld)["name"] == title
