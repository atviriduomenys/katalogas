import pytest
from django.conf import settings
from vitrina.structure import VersionStatus
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import ConceptFactory, LicenceFactory
from vitrina.classifiers.models import ConceptSchema, LANGUAGE_CONCEPT_SCHEMA_URI
from vitrina.datasets.factories import DatasetFactory, DatasetServiceFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.resources.factories import (
    CompressionFormatFactory,
    DatasetDistributionFactory,
    FileFormat,
    PackagingFormatFactory,
)
from vitrina.resources.models import (
    DatasetDistribution,
    DISTRIBUTION_AVAILABILITY_SCHEMA_URI,
    DISTRIBUTION_STANDARD_URI,
)
from vitrina.structure.factories import MetadataFactory, VersionFactory
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestDcatDistributionCreateView:
    def test_unauthenticated_redirects_to_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_no_permission_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        user = UserFactory()
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_nonexistent_dataset_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": 999999},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_nonexistent_organization_returns_404(self, app: DjangoTestApp):
        dataset = DatasetFactory(is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": 999999, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_dataset_not_in_organization_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        other_org = OrganizationFactory()
        dataset = DatasetFactory(organization=other_org, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_public_dataset_redirects_with_warning(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=True)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 302
        assert reverse("organization-detail", kwargs={"pk": org.pk}) in response.location

    def test_authorized_user_gets_200(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url)

        assert response.status_code == 200

    def test_coordinator_of_different_org_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        other_org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        user = UserFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(other_org),
            object_id=other_org.pk,
            role=Representative.RESOURCE_COORDINATOR,
            user=user,
        )
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_post_redirects_to_dcat_distribution_update_url(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["resource-form"]
        form["access_url"] = "https://example.com/data"
        response = form.submit()

        distribution = DatasetDistribution.objects.filter(dataset=dataset).first()
        assert distribution is not None

        assert response.status_code == 302
        expected_url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        assert response.location == expected_url

    def test_post_without_name_uses_default_distribution_name(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["resource-form"]
        form["access_url"] = "https://example.com/data"
        form.submit()

        distribution = DatasetDistribution.objects.filter(dataset=dataset).first()
        assert distribution is not None
        assert distribution.name == "resource1"

    def test_post_with_name_uses_provided_name(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["resource-form"]
        form["access_url"] = "https://example.com/data"
        form["name"] = "myresource"
        form.submit()

        distribution = DatasetDistribution.objects.filter(dataset=dataset).first()
        assert distribution is not None
        assert distribution.name == "myresource"

    def test_post_saves_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        data_service = DatasetServiceFactory(is_public=False)
        licence = LicenceFactory()
        file_format = FileFormat()
        compression_format = CompressionFormatFactory()
        packaging_format = PackagingFormatFactory()
        status_schema, _ = ConceptSchema.objects.get_or_create(uri=DatasetDistribution.DISTRIBUTION_STATUS_URI)
        status = ConceptFactory(concept_schemas=[status_schema])
        availability_schema, _ = ConceptSchema.objects.get_or_create(uri=DISTRIBUTION_AVAILABILITY_SCHEMA_URI)
        availability = ConceptFactory(concept_schemas=[availability_schema])
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        standard_schema, _ = ConceptSchema.objects.get_or_create(uri=DISTRIBUTION_STANDARD_URI)
        conforms_to_concept = ConceptFactory(concept_schemas=[standard_schema])
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-create",
            kwargs={"organization_id": org.pk, "dataset_id": dataset.pk},
        )
        form = app.get(url).forms["resource-form"]
        form["name"] = "myresource"
        form["access_url"] = "https://example.com/access"
        form["title"] = "My Distribution"
        form["description"] = "My description"
        form["data_service"] = data_service.pk
        form["licence"] = licence.pk
        form["format"] = file_format.pk
        form["compression_format"] = compression_format.pk
        form["packaging_format"] = packaging_format.pk
        form["download_url"] = "https://example.com/download.csv"
        form["conditions"] = "Some conditions"
        form["spatial_resolution"] = "100"
        form["temporal_resolution"] = "P1D"
        form["status"] = status.pk
        form["availability"] = availability.pk
        form["size"] = "1024"
        form["checksum_value"] = "abcdef123"
        form["checksum_algorithm"] = "MD5"
        form["issued"] = "2024-01-15"
        form["date_modified"] = "2024-06-01"
        form["language"] = language.pk
        form["conforms_to"] = [conforms_to_concept.pk]
        form["documentation"] = "https://example.com/doc"
        form.submit()

        distribution = DatasetDistribution.objects.filter(dataset=dataset).first()
        assert distribution is not None
        assert distribution.dataset == dataset
        assert distribution.name == "myresource"
        assert distribution.access_url == "https://example.com/access"
        assert distribution.title == "My Distribution"
        assert distribution.description == "My description"
        assert distribution.data_service == data_service
        assert distribution.licence == licence
        assert distribution.format == file_format
        assert distribution.compression_format == compression_format
        assert distribution.packaging_format == packaging_format
        assert distribution.download_url == "https://example.com/download.csv"
        assert distribution.conditions == "Some conditions"
        assert distribution.spatial_resolution == "100"
        assert distribution.temporal_resolution == "P1D"
        assert distribution.status == status
        assert distribution.availability == availability
        assert distribution.size == 1024
        assert distribution.checksum_value == "abcdef123"
        assert distribution.checksum_algorithm == "MD5"
        assert distribution.issued == "2024-01-15"
        assert str(distribution.date_modified) == "2024-06-01"
        assert distribution.language == language
        assert conforms_to_concept in distribution.conforms_to.all()
        assert distribution.documentation.filter(documentation_link="https://example.com/doc").exists()


class TestDcatDistributionUpdateView:
    def test_unauthenticated_redirects_to_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        response = app.get(url)

        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_no_permission_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        user = UserFactory()
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_user_with_permissions_for_different_distribution_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        other_dataset = DatasetFactory(organization=org)
        user = UserFactory(organization=org)
        RepresentativeFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(other_dataset),
            object_id=other_dataset.pk,
            user=user,
            role=Representative.RESOURCE_MANAGER,
        )
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_nonexistent_distribution_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": 999999,
            },
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_distribution_in_wrong_dataset_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        other_dataset = DatasetFactory(is_public=False)
        distribution = DatasetDistributionFactory(dataset=other_dataset)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_distribution_in_wrong_organization_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        other_org = OrganizationFactory()
        dataset = DatasetFactory(organization=other_org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        response = app.get(url, expect_errors=True)

        assert response.status_code == 404

    def test_public_dataset_redirects_with_warning(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=True)
        distribution = DatasetDistributionFactory(dataset=dataset)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        response = app.get(url)

        assert response.status_code == 302
        assert reverse("organization-detail", kwargs={"pk": org.pk}) in response.location

    def test_non_draft_metadata_version_redirects_with_error(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        version = VersionFactory(dataset=dataset, status=VersionStatus.STABLE)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update-versioned",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
                "version_id": version.pk,
            },
        )
        response = app.get(url)

        assert response.status_code == 302
        assert reverse("organization-detail", kwargs={"pk": org.pk}) in response.location

    def test_authorized_user_gets_200(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        response = app.get(url)

        assert response.status_code == 200

    def test_post_redirects_to_dcat_distribution_update_url(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        form = app.get(url).forms["resource-form"]
        form["access_url"] = "https://example.com/updated"
        response = form.submit()

        assert response.status_code == 302
        expected_url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        assert response.location == expected_url

    def test_post_updates_metadata_when_it_exists(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        metadata = MetadataFactory.create(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(distribution),
            object_id=distribution.pk,
            name="old-name",
            title="Old Title",
            description="Old description",
            version=1,
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        form = app.get(url).forms["resource-form"]
        form["access_url"] = "https://example.com/updated"
        form["name"] = "new-name"
        form["title"] = "New Title"
        form["description"] = "New description"
        form.submit()

        metadata.refresh_from_db()
        assert metadata.name == "new-name"
        assert metadata.title == "New Title"
        assert metadata.description == "New description"
        assert metadata.version == 2

    def test_post_updates_all_fields(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org, is_public=False)
        distribution = DatasetDistributionFactory(dataset=dataset)
        data_service = DatasetServiceFactory(is_public=False)
        licence = LicenceFactory()
        fmt = FileFormat()
        compression_fmt = CompressionFormatFactory()
        packaging_fmt = PackagingFormatFactory()
        status_schema, _ = ConceptSchema.objects.get_or_create(uri=DatasetDistribution.DISTRIBUTION_STATUS_URI)
        status = ConceptFactory(concept_schemas=[status_schema])
        availability_schema, _ = ConceptSchema.objects.get_or_create(uri=DISTRIBUTION_AVAILABILITY_SCHEMA_URI)
        availability = ConceptFactory(concept_schemas=[availability_schema])
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        standard_schema, _ = ConceptSchema.objects.get_or_create(uri=DISTRIBUTION_STANDARD_URI)
        conforms_to_concept = ConceptFactory(concept_schemas=[standard_schema])
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": org.pk,
                "dataset_id": dataset.pk,
                "distribution_id": distribution.pk,
            },
        )
        form = app.get(url).forms["resource-form"]
        form["name"] = "updatedresource"
        form["access_url"] = "https://example.com/updated-access"
        form["title"] = "Updated Distribution"
        form["description"] = "Updated description"
        form["data_service"] = data_service.pk
        form["licence"] = licence.pk
        form["format"] = fmt.pk
        form["compression_format"] = compression_fmt.pk
        form["packaging_format"] = packaging_fmt.pk
        form["download_url"] = "https://example.com/updated-download.csv"
        form["conditions"] = "Updated conditions"
        form["spatial_resolution"] = "200"
        form["temporal_resolution"] = "P1M"
        form["status"] = status.pk
        form["availability"] = availability.pk
        form["size"] = "2048"
        form["checksum_value"] = "fedcba987"
        form["checksum_algorithm"] = "SHA256"
        form["issued"] = "2024-03-10"
        form["date_modified"] = "2024-09-01"
        form["language"] = language.pk
        form["conforms_to"] = [conforms_to_concept.pk]
        form["documentation"] = "https://example.com/updated-doc"
        form.submit()

        distribution.refresh_from_db()
        assert distribution.name == "updatedresource"
        assert distribution.access_url == "https://example.com/updated-access"
        assert distribution.title == "Updated Distribution"
        assert distribution.description == "Updated description"
        assert distribution.data_service == data_service
        assert distribution.licence == licence
        assert distribution.format == fmt
        assert distribution.compression_format == compression_fmt
        assert distribution.packaging_format == packaging_fmt
        assert distribution.download_url == "https://example.com/updated-download.csv"
        assert distribution.conditions == "Updated conditions"
        assert distribution.spatial_resolution == "200"
        assert distribution.temporal_resolution == "P1M"
        assert distribution.status == status
        assert distribution.availability == availability
        assert distribution.size == 2048
        assert distribution.checksum_value == "fedcba987"
        assert distribution.checksum_algorithm == "SHA256"
        assert distribution.issued == "2024-03-10"
        assert str(distribution.date_modified) == "2024-09-01"
        assert distribution.language == language
        assert conforms_to_concept in distribution.conforms_to.all()
        assert distribution.documentation.filter(documentation_link="https://example.com/updated-doc").exists()
