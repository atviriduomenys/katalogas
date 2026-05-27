import uuid
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.catalogs.models import Catalog
from vitrina.classifiers.factories import (
    ActivityFactory,
    CategoryFactory,
    ConceptFactory,
    FrequencyFactory,
    LicenceFactory,
    ProvenanceStatementFactory,
    RuleFactory,
)
from vitrina.classifiers.models import ConceptSchema, LANGUAGE_CONCEPT_SCHEMA_URI
from vitrina.datasets.form_helpers import DATASET_STANDARD_URI
from vitrina.datasets.factories import (
    AttributionFactory,
    ContactFactory,
    DatasetAttributionFactory,
    DatasetFactory,
    DCATResourceSubclassFactory,
    RelationFactory,
)
from vitrina.datasets.models import (
    Attribution,
    DatasetAttribution,
    DatasetQualifiedRelation,
    DatasetRelation,
    Dataset,
    DCATResourceSubclass,
    Relation,
)
from vitrina.dcat.forms.dataset_forms import (
    DatasetResourceForm,
    InformationSystemResourceForm,
    ServiceResourceForm,
    InformationSystemUpdateForm,
    ServiceUpdateForm,
    DatasetUpdateForm,
)
from vitrina.identifiers.factories import IdentifierFactory
from vitrina.identifiers.models import Identifier, Agency
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

    def test_post_redirects_to_dcat_update_url(self, app: DjangoTestApp):
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
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Test Redirect"
        form["description"] = "Test redirect description"
        form["name"] = "testredirect"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        response = form.submit()

        dataset = Dataset.objects.filter(translations__title="Test Redirect").first()
        assert dataset is not None
        assert response.status_code == 200

    def test_post_information_system_saves_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        publisher_org = OrganizationFactory()
        creator_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        category = CategoryFactory()
        FrequencyFactory(title="Nežinomas")
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "IS All Fields"
        form["description"] = "IS description"
        form["name"] = "isallfields"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(publisher_org.pk)]
        form["creator"].force_value(str(creator_org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        form["landing_page"] = "https://example.com/landing"
        form["conditions"] = "Some conditions text"
        form["tags"] = "tagA, tagB"
        form["identifier"] = "5678"
        form["languages"] = [str(language.pk)]
        form["category"].force_value([str(category.pk)])
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
        assert dataset.information_system_publishers.filter(pk=publisher_org.pk).exists()
        assert DatasetAttribution.objects.filter(
            dataset=dataset, attribution__name=Attribution.CREATOR, organization=creator_org
        ).exists()
        assert dataset.information_system_assessment_url == "https://example.com/assessment"
        assert dataset.landing_page == "https://example.com/landing"
        assert dataset.conditions == "Some conditions text"
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"taga", "tagb"}
        assert dataset.languages.filter(pk=language.pk).exists()
        assert dataset.category.filter(pk=category.pk).exists()
        assert Identifier.objects.filter(resource=dataset, notation="5678").exists()
        assert Metadata.objects.get(dataset=dataset).name == f"{org.name}isallfields"
        assert Version.objects.filter(dataset=dataset).count() == 1

    def test_post_service_saves_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        contact = ContactFactory(organization=org)
        licence = LicenceFactory()
        rule = RuleFactory()
        category = CategoryFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Service All Fields"
        form["name"] = "serviceallfields"
        form["tags"] = "svcTag"
        form["organization"].force_value(str(org.pk))
        form["contact"] = contact.pk
        form["endpoint_url"] = "https://api.example.com"
        form["endpoint_description"] = "https://api.example.com/spec"
        form["access_rights"] = Dataset.RESTRICTED
        form["landing_page"] = "https://example.com/service"
        form["license"] = licence.pk
        form["follows"] = [str(rule.pk)]
        form["service_quality"] = ["https://quality.example.com"]
        form["category"].force_value([str(category.pk)])
        form.submit()

        dataset = Dataset.objects.filter(translations__title="Service All Fields").first()
        assert dataset is not None

        # Automatically set fields
        assert dataset.subclass == subclass
        assert dataset.is_public is False
        assert dataset.service is True
        assert dataset.catalog == Catalog.objects.get(identifier=Catalog.IDENTIFIER_ISRIS)

        # Form set fields
        assert dataset.organization == org
        assert dataset.title == "Service All Fields"
        assert dataset.endpoint_url == "https://api.example.com"
        assert dataset.endpoint_description == "https://api.example.com/spec"
        assert dataset.access_rights == Dataset.RESTRICTED
        assert dataset.landing_page == "https://example.com/service"
        assert dataset.contact == contact
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"svctag"}
        assert dataset.license == licence
        assert dataset.follows.filter(pk=rule.pk).exists()
        assert dataset.service_quality.filter(url="https://quality.example.com").exists()
        assert dataset.category.filter(pk=category.pk).exists()

    def test_post_dataset_saves_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        frequency = FrequencyFactory()
        contact = ContactFactory(organization=org)
        dataset_standard_schema, _ = ConceptSchema.objects.get_or_create(uri=DATASET_STANDARD_URI)
        conforms_to_concept = ConceptFactory(concept_schemas=[dataset_standard_schema])
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        provenance = ProvenanceStatementFactory()
        dataset_type_schema, _ = ConceptSchema.objects.get_or_create(uri=Dataset.DATASET_TYPE_SCHEME_URI)
        dataset_type = ConceptFactory(concept_schemas=[dataset_type_schema])
        activity = ActivityFactory()
        creator_attribution = Attribution.objects.get(name=Attribution.CREATOR)
        creator_org = OrganizationFactory()
        category = CategoryFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Dataset All Fields"
        form["description"] = "Dataset description"
        form["name"] = "datasetallfields"
        form["access_rights"] = Dataset.RESTRICTED
        form["frequency"] = frequency.pk
        form["landing_page"] = "https://example.com/dataset"
        form["temporal_start"] = "2024-01-01"
        form["temporal_end"] = "2024-12-31"
        form["spatial_resolution"] = "100"
        form["temporal_resolution"] = "P1D"
        form["contact"] = contact.pk
        form["tags"] = "dataTag"
        form["organization"].force_value(str(org.pk))
        form["conforms_to"] = conforms_to_concept.pk
        form["languages"] = [str(language.pk)]
        form["provenance"] = [str(provenance.pk)]
        form["dataset_type"] = dataset_type.pk
        form["was_generated_by"] = [str(activity.pk)]
        form["qualified_relation"] = "https://example.com/relation"
        form["version_notes"] = "Initial version"
        form["creator"].force_value(str(creator_org.pk))
        form["category"].force_value([str(category.pk)])
        form.submit()

        dataset = Dataset.objects.filter(translations__title="Dataset All Fields").first()
        assert dataset is not None

        # Automatically set fields
        assert dataset.subclass == subclass
        assert dataset.is_public is False
        assert dataset.catalog == Catalog.objects.get(identifier=Catalog.IDENTIFIER_ISRIS)

        # Form set fields
        assert dataset.organization == org
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
        assert dataset.conforms_to == conforms_to_concept
        assert dataset.languages.filter(pk=language.pk).exists()
        assert dataset.provenance.filter(pk=provenance.pk).exists()
        assert dataset.dataset_type == dataset_type
        assert dataset.was_generated_by.filter(pk=activity.pk).exists()
        assert dataset.category.filter(pk=category.pk).exists()
        assert Metadata.objects.get(dataset=dataset).name == f"{org.name}datasetallfields"
        assert DatasetQualifiedRelation.objects.filter(dataset=dataset, url="https://example.com/relation").exists()
        assert dataset.version_notes == "Initial version"
        assert DatasetAttribution.objects.filter(
            dataset=dataset, attribution=creator_attribution, organization=creator_org
        ).exists()

    def test_post_saves_dataset_with_parent(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        parent = DatasetFactory(organization=org, subclass=subclass, is_public=False)
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
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Child Dataset"
        form["description"] = "Child description"
        form["name"] = "child"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
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
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Test Dataset"
        form["description"] = "Dataset description"
        form["name"] = "dataset"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        form.submit()

        dataset = Dataset.objects.filter(translations__title="Test Dataset").first()
        assert dataset is not None
        assert dataset.get_parent() is None

    def test_post_service_redirects_to_instance_organization(self, app: DjangoTestApp):
        url_org = OrganizationFactory()
        form_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": url_org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Service Redirect Test"
        form["name"] = "redirect"
        form["tags"] = "tag1"
        form["organization"].force_value(str(form_org.pk))
        form["endpoint_url"] = "https://api.example.com"
        form["endpoint_description"] = "https://api.example.com/spec"
        response = form.submit()

        dataset = Dataset.objects.filter(translations__title="Service Redirect Test").first()
        assert dataset is not None
        assert dataset.organization == form_org
        assert response.status_code == 200

    def test_post_dataset_redirects_to_instance_organization(self, app: DjangoTestApp):
        url_org = OrganizationFactory()
        form_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        frequency = FrequencyFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-create",
            kwargs={"organization_id": url_org.pk, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Dataset Redirect Test"
        form["description"] = "Test description"
        form["name"] = "redirect"
        form["organization"].force_value(str(form_org.pk))
        form["frequency"] = frequency.pk
        form["version_notes"] = "v1"
        response = form.submit()

        dataset = Dataset.objects.filter(translations__title="Dataset Redirect Test").first()
        assert dataset is not None
        assert dataset.organization == form_org
        assert response.status_code == 200


class TestDcatDatasetUpdateView:
    def test_unauthenticated_redirects_to_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_no_permission_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory()
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_user_with_different_organization_permissions_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        new_organization = OrganizationFactory()
        user = UserFactory(organization=new_organization)
        RepresentativeFactory(
            organization=new_organization,
            content_type=ContentType.objects.get_for_model(new_organization),
            object_id=new_organization.pk,
            user=user,
            role=Representative.RESOURCE_MANAGER,
        )
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_user_with_different_dataset_permissions_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        new_dataset = DatasetFactory(organization=org)
        user = UserFactory(organization=org)
        RepresentativeFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(new_dataset),
            object_id=new_dataset.pk,
            user=user,
            role=Representative.RESOURCE_MANAGER,
        )
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_user_with_correct_organization_permissions_returns_200(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory(organization=org)
        RepresentativeFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.pk,
            user=user,
            role=Representative.RESOURCE_MANAGER,
        )
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 200

    def test_user_with_correct_dataset_permissions_returns_200(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory(organization=org)
        RepresentativeFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=Representative.RESOURCE_MANAGER,
        )
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 200

    def test_nonexistent_organization_returns_404(self, app: DjangoTestApp):
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(subclass=subclass, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": 999999, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_nonexistent_dataset_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": 999999},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_dataset_not_in_organization_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        other_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=other_org, subclass=subclass, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_coordinator_of_different_org_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        other_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(other_org),
            object_id=other_org.pk,
            role=Representative.RESOURCE_COORDINATOR,
            user=user,
        )
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_public_dataset_redirects_with_warning(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=True)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 200
        assert "notification" in response.text

    def test_invalid_subclass_redirects_with_warning(self, app: DjangoTestApp):
        org = OrganizationFactory()
        catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
        dataset = DatasetFactory(organization=org, subclass=catalog_subclass, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 200
        assert "notification" in response.text

    @pytest.mark.parametrize(
        "subclass_name, expected_form_class",
        [
            (DCATResourceSubclass.INFORMATION_SYSTEM, InformationSystemUpdateForm),
            (DCATResourceSubclass.SERVICE, ServiceUpdateForm),
            (DCATResourceSubclass.DATASET, DatasetUpdateForm),
        ],
    )
    def test_get_uses_correct_form_per_subclass(self, app: DjangoTestApp, subclass_name: str, expected_form_class):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=subclass_name)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 200
        assert type(response.context["form"]) is expected_form_class

    def test_post_redirects_to_dcat_update_url(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Redirect Test"
        form["description"] = "Redirect description"
        form["name"] = "redirect"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        response = form.submit()

        assert response.status_code == 200

    def test_post_service_redirects_to_instance_organization(self, app: DjangoTestApp):
        org = OrganizationFactory()
        new_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        dataset = DatasetFactory(
            organization=org,
            subclass=subclass,
            is_public=False,
            service=True,
            endpoint_url="https://api.example.com",
            endpoint_description="https://api.example.com/spec",
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Service Update Redirect"
        form["name"] = "redrect"
        form["tags"] = "tag1"
        form["organization"].force_value(str(new_org.pk))
        response = form.submit()

        dataset.refresh_from_db()
        assert dataset.organization == new_org
        assert response.status_code == 200

    def test_post_dataset_redirects_to_instance_organization(self, app: DjangoTestApp):
        org = OrganizationFactory()
        new_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Dataset Update Redirect"
        form["description"] = "Dataset description"
        form["name"] = "redirect"
        form["organization"].force_value(str(new_org.pk))
        form["version_notes"] = "v1"
        response = form.submit()

        dataset.refresh_from_db()
        assert dataset.organization == new_org
        assert response.status_code == 200

    def test_post_information_system_updates_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        publisher_org = OrganizationFactory()
        creator_org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        old_importance = ConceptFactory(concept_schemas=[importance_schema])
        new_importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        old_is_type = ConceptFactory(concept_schemas=[is_type_schema])
        new_is_type = ConceptFactory(concept_schemas=[is_type_schema])
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        category = CategoryFactory()
        dataset = DatasetFactory(
            organization=org,
            subclass=subclass,
            is_public=False,
            information_system_importance=old_importance,
            information_system_type=old_is_type,
            information_system_publishers=[org],
        )
        DatasetAttributionFactory(
            dataset=dataset,
            attribution=Attribution.objects.get(name=Attribution.CREATOR),
            organization=org,
        )
        agency = Agency.objects.get(code=Agency.RISR_CODE)
        IdentifierFactory(resource=dataset, scheme_agency=agency, notation="1111")
        catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
        catalog_dataset = DatasetFactory(organization=org, subclass=catalog_subclass, is_public=False)
        other_is = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        other_is2 = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        catalog_relation = RelationFactory(name=Relation.CATALOG)
        rti_relation = RelationFactory(name=Relation.RELATES_TO_INFORMATION_SYSTEM)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Updated IS Title"
        form["description"] = "Updated IS description"
        form["name"] = "updateis"
        form["information_system_importance"] = new_importance.pk
        form["information_system_type"] = new_is_type.pk
        form["information_system_publishers"] = [str(publisher_org.pk)]
        form["creator"].force_value(str(creator_org.pk))
        form["information_system_assessment_url"] = "https://example.com/updated-assessment"
        form["landing_page"] = "https://example.com/updated"
        form["conditions"] = "Updated conditions"
        form["tags"] = "updatedTag"
        form["applicable_legislation"] = "https://example.com/law"
        form["identifier"] = "9999"
        form["languages"] = [str(language.pk)]
        form["has_part"].force_value([str(catalog_dataset.pk)])
        form["relates_to_information_system"].force_value([str(other_is.pk)])
        form["related_information_system"].force_value([str(other_is2.pk)])
        form["category"].force_value([str(category.pk)])

        with patch("vitrina.datasets.models.update_applicable_legislation_description"):
            form.submit()

        dataset.refresh_from_db()
        assert dataset.title == "Updated IS Title"
        assert dataset.description == "Updated IS description"
        assert dataset.information_system_importance == new_importance
        assert dataset.information_system_type == new_is_type
        assert dataset.information_system_publishers.filter(pk=publisher_org.pk).exists()
        assert DatasetAttribution.objects.filter(
            dataset=dataset, attribution__name=Attribution.CREATOR, organization=creator_org
        ).exists()
        assert dataset.information_system_assessment_url == "https://example.com/updated-assessment"
        assert dataset.landing_page == "https://example.com/updated"
        assert dataset.conditions == "Updated conditions"
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"updatedtag"}
        assert dataset.languages.filter(pk=language.pk).exists()
        assert dataset.category.filter(pk=category.pk).exists()
        assert dataset.applicable_legislation.filter(url="https://example.com/law").exists()
        assert Identifier.objects.filter(resource=dataset).count() == 1
        assert Identifier.objects.filter(resource=dataset, notation="9999").exists()
        assert DatasetRelation.objects.filter(
            relation=catalog_relation, dataset=dataset, part_of=catalog_dataset
        ).exists()
        assert DatasetRelation.objects.filter(relation=rti_relation, dataset=other_is, part_of=dataset).exists()
        assert DatasetRelation.objects.filter(relation=rti_relation, dataset=dataset, part_of=other_is2).exists()

    def test_post_service_updates_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        contact = ContactFactory(organization=org)
        service_type_schema, _ = ConceptSchema.objects.get_or_create(uri=Dataset.SERVICE_TYPE_SCHEME_URI)
        service_type_concept = ConceptFactory(concept_schemas=[service_type_schema])
        licence = LicenceFactory()
        rule = RuleFactory()
        category = CategoryFactory()
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False, service=True)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        served_dataset = DatasetFactory(organization=org, subclass=dataset_subclass, is_public=False)
        service_relation = RelationFactory(name=Relation.SERVICE)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Updated Service Title"
        form["name"] = "updatesvc"
        form["tags"] = "updatedSvcTag"
        form["contact"] = contact.pk
        form["endpoint_url"] = "https://api.updated.com"
        form["endpoint_description"] = "https://api.updated.com/spec"
        form["access_rights"] = Dataset.RESTRICTED
        form["landing_page"] = "https://example.com/updated-svc"
        form["service_type"] = [str(service_type_concept.pk)]
        form["license"] = licence.pk
        form["follows"] = [str(rule.pk)]
        form["service_quality"] = ["https://quality.example.com/updated"]
        form["serves_datasets"].force_value([str(served_dataset.pk)])
        form["category"].force_value([str(category.pk)])
        form.submit()

        dataset.refresh_from_db()
        assert dataset.title == "Updated Service Title"
        assert dataset.endpoint_url == "https://api.updated.com"
        assert dataset.endpoint_description == "https://api.updated.com/spec"
        assert dataset.access_rights == Dataset.RESTRICTED
        assert dataset.landing_page == "https://example.com/updated-svc"
        assert dataset.contact == contact
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"updatedsvctag"}
        assert dataset.service_type.filter(pk=service_type_concept.pk).exists()
        assert dataset.license == licence
        assert dataset.follows.filter(pk=rule.pk).exists()
        assert dataset.service_quality.filter(url="https://quality.example.com/updated").exists()
        assert dataset.category.filter(pk=category.pk).exists()
        assert DatasetRelation.objects.filter(
            relation=service_relation, dataset=dataset, part_of=served_dataset
        ).exists()

    def test_post_dataset_updates_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        frequency = FrequencyFactory()
        contact = ContactFactory(organization=org)
        dataset_standard_schema, _ = ConceptSchema.objects.get_or_create(uri=DATASET_STANDARD_URI)
        conforms_to_concept = ConceptFactory(concept_schemas=[dataset_standard_schema])
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        provenance = ProvenanceStatementFactory()
        dataset_type_schema, _ = ConceptSchema.objects.get_or_create(uri=Dataset.DATASET_TYPE_SCHEME_URI)
        dataset_type = ConceptFactory(concept_schemas=[dataset_type_schema])
        activity = ActivityFactory()
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        contributor = AttributionFactory(name=Attribution.CONTRIBUTOR)
        attribution_org = OrganizationFactory()
        creator_attribution = Attribution.objects.get(name=Attribution.CREATOR)
        creator_org = OrganizationFactory()
        category = CategoryFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Updated Dataset Title"
        form["description"] = "Updated dataset description"
        form["name"] = "updateds"
        form["access_rights"] = Dataset.RESTRICTED
        form["frequency"] = frequency.pk
        form["landing_page"] = "https://example.com/updated-ds"
        form["temporal_start"] = "2025-01-01"
        form["temporal_end"] = "2025-12-31"
        form["spatial_resolution"] = "200"
        form["temporal_resolution"] = "P1M"
        form["contact"] = contact.pk
        form["tags"] = "updatedDataTag"
        form["documentation"] = "https://example.com/doc"
        form["applicable_legislation"] = "https://example.com/law"
        form["conforms_to"] = conforms_to_concept.pk
        form["languages"] = [str(language.pk)]
        form["provenance"] = [str(provenance.pk)]
        form["dataset_type"] = dataset_type.pk
        form["was_generated_by"] = [str(activity.pk)]
        form["qualified_attribution"].force_value([str(attribution_org.pk)])
        form["qualified_relation"] = "https://example.com/relation"
        form["version_notes"] = "Updated version notes"
        form["creator"].force_value(str(creator_org.pk))
        form["category"].force_value([str(category.pk)])
        with patch("vitrina.datasets.models.update_applicable_legislation_description"):
            form.submit()

        dataset.refresh_from_db()
        assert dataset.title == "Updated Dataset Title"
        assert dataset.description == "Updated dataset description"
        assert dataset.access_rights == Dataset.RESTRICTED
        assert dataset.frequency == frequency
        assert dataset.landing_page == "https://example.com/updated-ds"
        assert str(dataset.temporal_start) == "2025-01-01"
        assert str(dataset.temporal_end) == "2025-12-31"
        assert dataset.spatial_resolution == "200"
        assert dataset.temporal_resolution == "P1M"
        assert dataset.contact == contact
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"updateddatatag"}
        assert dataset.documentation.filter(documentation_link="https://example.com/doc").exists()
        assert dataset.applicable_legislation.filter(url="https://example.com/law").exists()
        assert dataset.conforms_to == conforms_to_concept
        assert dataset.languages.filter(pk=language.pk).exists()
        assert dataset.provenance.filter(pk=provenance.pk).exists()
        assert dataset.dataset_type == dataset_type
        assert dataset.was_generated_by.filter(pk=activity.pk).exists()
        assert dataset.category.filter(pk=category.pk).exists()
        assert DatasetAttribution.objects.filter(
            dataset=dataset, attribution=contributor, organization=attribution_org
        ).exists()
        assert DatasetQualifiedRelation.objects.filter(dataset=dataset, url="https://example.com/relation").exists()
        assert dataset.version_notes == "Updated version notes"
        assert DatasetAttribution.objects.filter(
            dataset=dataset, attribution=creator_attribution, organization=creator_org
        ).exists()

    def test_post_updates_metadata_title_and_name(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        dataset = DatasetFactory(
            organization=org,
            subclass=subclass,
            is_public=False,
            information_system_importance=importance,
            information_system_type=is_type,
            information_system_publishers=[org],
        )
        DatasetAttributionFactory(
            dataset=dataset,
            attribution=Attribution.objects.get(name=Attribution.CREATOR),
            organization=org,
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "New Title"
        form["description"] = "New description"
        form["name"] = "newname"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        form.submit()

        metadata = Metadata.objects.get(dataset=dataset)
        assert metadata.title == "New Title"
        assert metadata.description == "New description"
        assert metadata.name == f"{org.name}newname"
        assert metadata.draft is True

    def test_post_changes_parent(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        parent = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "IS Title"
        form["description"] = "IS description"
        form["name_prefix"].force_value(f"{parent.name}")
        form["name"] = "updateis"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        form["parent"] = parent.pk
        form.submit()

        dataset.refresh_from_db()
        assert dataset.get_parent().pk == parent.pk

    def test_post_removes_parent(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        parent = DatasetFactory(organization=org, subclass=subclass, is_public=True)
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        dataset.move(parent, "sorted-child")
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "IS Title"
        form["description"] = "IS description"
        form["name_prefix"].force_value(f"{org.name}")
        form["name"] = "updateis"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        form["parent"].force_value("")
        form.submit()

        dataset.refresh_from_db()
        assert dataset.get_parent() is None

    def test_post_sets_status_has_data_when_endpoint_url_changes_on_service(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        contact = ContactFactory(organization=org)
        dataset = DatasetFactory(
            organization=org,
            subclass=subclass,
            is_public=False,
            service=True,
            status=Dataset.UNASSIGNED,
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Service Title"
        form["name"] = "updatesvc"
        form["tags"] = "svcTag"
        form["contact"] = contact.pk
        form["endpoint_url"] = "https://api.new.com"
        form["endpoint_description"] = "https://api.new.com/spec"
        form.submit()

        dataset.refresh_from_db()
        assert dataset.status == Dataset.HAS_DATA

    def test_post_sets_status_inventored_when_endpoint_url_changes_without_service_flag(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        contact = ContactFactory(organization=org)
        # service=False: endpoint_url change won't trigger HAS_DATA
        dataset = DatasetFactory(
            organization=org,
            subclass=subclass,
            is_public=False,
            service=False,
            status=Dataset.UNASSIGNED,
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "Service Title"
        form["name"] = "updatesvc"
        form["tags"] = "svcTag"
        form["contact"] = contact.pk
        form["endpoint_url"] = "https://api.new.com"
        form["endpoint_description"] = "https://api.new.com/spec"
        form.submit()

        dataset.refresh_from_db()
        assert dataset.status == Dataset.INVENTORED

    def test_post_sets_status_unassigned_when_not_public_and_has_published_date(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])
        is_type_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI)
        is_type = ConceptFactory(concept_schemas=[is_type_schema])
        # DatasetFactory sets published and status=HAS_DATA by default
        dataset = DatasetFactory(organization=org, subclass=subclass, is_public=False)
        assert dataset.published is not None
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        # IS form has no endpoint_url field, so endpoint_url won't be in changed_data
        form = app.get(url).forms["wizard-fragment-form"]
        form["title"] = "IS Title"
        form["description"] = "IS description"
        form["name"] = "updateis"
        form["identifier"] = "1234"
        form["information_system_importance"] = importance.pk
        form["information_system_type"] = is_type.pk
        form["information_system_publishers"] = [str(org.pk)]
        form["creator"].force_value(str(org.pk))
        form["information_system_assessment_url"] = "https://example.com/assessment"
        form.submit()

        dataset.refresh_from_db()
        assert dataset.published is None
        assert dataset.status == Dataset.UNASSIGNED
