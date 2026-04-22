import uuid

import pytest
from django.conf import settings
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.catalogs.models import Catalog
from vitrina.classifiers.factories import ConceptFactory, FrequencyFactory
from vitrina.classifiers.models import ConceptSchema
from vitrina.datasets.factories import ContactFactory, DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.dcat.forms import (
    DatasetResourceForm,
    InformationSystemResourceForm,
    ServiceResourceForm,
)
from vitrina.identifiers.models import Identifier
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.structure.models import Metadata, Version
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestDcatDatasetCreateView:
    def test_unauthenticated_redirects_to_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        response = app.get(url)

        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_no_permission_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        user = UserFactory()
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_nonexistent_organization_returns_404(self, app: DjangoTestApp):
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": 999999, "subclass_uuid": subclass.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_nonexistent_subclass_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": uuid.uuid4()},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_coordinator_of_different_org_returns_403(self, app: DjangoTestApp):
        from django.contrib.contenttypes.models import ContentType

        org = OrganizationFactory()
        other_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        user = UserFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(other_org),
            object_id=other_org.pk,
            role=Representative.RESOURCE_COORDINATOR,
            user=user,
        )
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_invalid_subclass_redirects_with_error(self, app: DjangoTestApp):
        org = OrganizationFactory()
        catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": catalog_subclass.pk},
        )
        response = app.get(url)

        assert response.status_code == 302
        assert reverse("organization-detail", kwargs={"pk": org.pk}) in response.location

    @pytest.mark.parametrize(
        "subclass_name, expected_form_class",
        [
            (DCATResourceSubclass.INFORMATION_SYSTEM, InformationSystemResourceForm),
            (DCATResourceSubclass.SERVICE, ServiceResourceForm),
            (DCATResourceSubclass.DATASET, DatasetResourceForm),
        ],
    )
    def test_get_uses_correct_form_per_subclass(self, app: DjangoTestApp, subclass_name: str, expected_form_class):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=subclass_name)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        response = app.get(url)

        assert response.status_code == 200
        assert type(response.context["form"]) is expected_form_class

    def test_post_redirects_to_dcat_create_url(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        FrequencyFactory(title="Nežinomas")
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "Test Redirect"
        form["description"] = "Test redirect description"
        form["name"] = f"{org.name}testredirect"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publisher"] = org.pk
        form["information_system_creator"] = org.pk
        response = form.submit()

        assert response.status_code == 302
        expected_url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": str(subclass.pk)},
        )
        assert response.location == expected_url

    def test_post_information_system_saves_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        publisher_org = OrganizationFactory()
        creator_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        FrequencyFactory(title="Nežinomas")
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "IS All Fields"
        form["description"] = "IS description"
        form["name"] = f"{org.name}isallfields"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publisher"] = publisher_org.pk
        form["information_system_creator"] = creator_org.pk
        form["landing_page"] = "https://example.com/landing"
        form["conditions"] = "Some conditions text"
        form["tags"] = "tagA, tagB"
        form["identifier"] = "5678"
        form.submit()

        dataset = Dataset.objects.filter(translations__title="IS All Fields").first()
        assert dataset is not None

        # Automatically set fields
        assert dataset.organization == org
        assert dataset.subclass == subclass
        assert dataset.is_public is False
        assert dataset.access_rights == Dataset.CONFIDENTIAL
        assert dataset.catalog == Catalog.objects.get(identifier=Catalog.IDENTIFIER_ISRIS)

        # Form set fields
        assert dataset.title == "IS All Fields"
        assert dataset.description == "IS description"
        assert dataset.information_system_importance == importance
        assert dataset.information_system_type == is_type
        assert dataset.information_system_publisher == publisher_org
        assert dataset.information_system_creator == creator_org
        assert dataset.landing_page == "https://example.com/landing"
        assert dataset.conditions == "Some conditions text"
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"taga", "tagb"}
        assert Identifier.objects.filter(resource=dataset, notation="5678").exists()
        assert Metadata.objects.get(dataset=dataset).name == f"{org.name}isallfields"
        assert Version.objects.filter(dataset=dataset).count() == 1

    def test_post_service_saves_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        contact = ContactFactory(organization=org)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "Service All Fields"
        form["name"] = f"{org.name}serviceallfields"
        form["tags"] = "svcTag"
        form["contact"] = contact.pk
        form["endpoint_url"] = "https://api.example.com"
        form["endpoint_description"] = "https://api.example.com/spec"
        form["access_rights"] = Dataset.RESTRICTED
        form["landing_page"] = "https://example.com/service"
        form.submit()

        dataset = Dataset.objects.filter(translations__title="Service All Fields").first()
        assert dataset is not None

        # Automatically set fields
        assert dataset.organization == org
        assert dataset.subclass == subclass
        assert dataset.is_public is False
        assert dataset.service is True
        assert dataset.catalog == Catalog.objects.get(identifier=Catalog.IDENTIFIER_ISRIS)

        # Form set fields
        assert dataset.title == "Service All Fields"
        assert dataset.endpoint_url == "https://api.example.com"
        assert dataset.endpoint_description == "https://api.example.com/spec"
        assert dataset.access_rights == Dataset.RESTRICTED
        assert dataset.landing_page == "https://example.com/service"
        assert dataset.contact == contact
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"svctag"}

    def test_post_dataset_saves_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        frequency = FrequencyFactory()
        contact = ContactFactory(organization=org)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "Dataset All Fields"
        form["description"] = "Dataset description"
        form["name"] = f"{org.name}datasetallfields"
        form["access_rights"] = Dataset.RESTRICTED
        form["frequency"] = frequency.pk
        form["landing_page"] = "https://example.com/dataset"
        form["temporal_start"] = "2024-01-01"
        form["temporal_end"] = "2024-12-31"
        form["spatial_resolution"] = "100"
        form["temporal_resolution"] = "P1D"
        form["contact"] = contact.pk
        form["tags"] = "dataTag"
        form.submit()

        dataset = Dataset.objects.filter(translations__title="Dataset All Fields").first()
        assert dataset is not None

        # Automatically set fields
        assert dataset.organization == org
        assert dataset.subclass == subclass
        assert dataset.is_public is False
        assert dataset.catalog == Catalog.objects.get(identifier=Catalog.IDENTIFIER_ISRIS)

        # Form set fields
        assert dataset.title == "Dataset All Fields"
        assert dataset.description == "Dataset description"
        assert dataset.access_rights == Dataset.RESTRICTED
        assert dataset.frequency == frequency
        assert dataset.landing_page == "https://example.com/dataset"
        assert str(dataset.temporal_start) == "2024-01-01"
        assert str(dataset.temporal_end) == "2024-12-31"
        assert dataset.spatial_resolution == "100"
        assert dataset.temporal_resolution == "P1D"
        assert dataset.contact == contact
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"datatag"}
        assert Metadata.objects.get(dataset=dataset).name == f"{org.name}datasetallfields"

    def test_post_saves_dataset_with_parent(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        parent = DatasetFactory(organization=org, subclass=subclass)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        FrequencyFactory(title="Nežinomas")
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create-with-parent",
            kwargs={"organization_id": org.pk, "parent_id": parent.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "Child Dataset"
        form["description"] = "Child description"
        form["name"] = f"{org.name}child"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publisher"] = org.pk
        form["information_system_creator"] = org.pk
        form.submit()

        child = Dataset.objects.filter(translations__title="Child Dataset").first()
        assert child is not None
        assert child.get_parent().pk == parent.pk

    def test_post_saves_dataset_without_parent(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        FrequencyFactory(title="Nežinomas")
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "Test Dataset"
        form["description"] = "Dataset description"
        form["name"] = f"{org.name}dataset"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publisher"] = org.pk
        form["information_system_creator"] = org.pk
        form.submit()

        dataset = Dataset.objects.filter(translations__title="Test Dataset").first()
        assert dataset is not None
        assert dataset.get_parent() is None
