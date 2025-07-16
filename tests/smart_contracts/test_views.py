import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.smart_contracts.models import Agreement, AgreementScope
from vitrina.structure.factories import MetadataFactory
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestAgreementCreateView:
    def test_cannot_create_agreement_without_permission(
        self, app: DjangoTestApp
    ) -> None:
        user = UserFactory()
        project = ProjectFactory()
        app.set_user(user)

        response = app.get(
            reverse("agreement-create", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 403

    def test_cannot_create_agreement_for_deleted_project(
        self, app: DjangoTestApp
    ) -> None:
        user = UserFactory()
        project = ProjectFactory(user=user, deleted=True)
        app.set_user(user)

        response = app.get(
            reverse("agreement-create", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 404

    def test_cannot_create_agreement_for_project_if_one_already_exists(
        self, app: DjangoTestApp
    ) -> None:
        organization = OrganizationFactory()
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user)
        AgreementFactory(project=project, assigner_organization=organization)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        assert response.status_code == 302
        assert response.url == reverse("project-datasets", args=[project.pk])

    def test_creates_agreement_and_scopes(self, app: DjangoTestApp) -> None:
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            dataset=dataset,
            name="test/dataset",
        )
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset])
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]
        form["form-0-scopes"] = ["test_dataset_getall"]
        response = form.submit()

        assert response.status_code == 302
        assert response.url == reverse("project-detail", args=[project.pk])

        agreement = Agreement.objects.get(project=project, assigner_organization=organization)
        assert agreement.status == AgreementStatuses.CREATED
        assert agreement.is_agent_sync_enabled is False
        assert agreement.agreementscope_set.count() == 1

        agreement_scope = agreement.agreementscope_set.first()
        assert agreement_scope.resource == "test_dataset_getall"
        assert agreement_scope.action == "getall"

    def test_creates_multiple_agreements_and_scopes(self, app: DjangoTestApp) -> None:
        organization = OrganizationFactory()
        dataset1 = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset1),
            object_id=dataset1.pk,
            dataset=dataset1,
            name="test/dataset1",
        )
        dataset2 = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset2),
            object_id=dataset2.pk,
            dataset=dataset2,
            name="test/dataset2",
        )
        diff_organization = OrganizationFactory()
        diff_dataset = DatasetFactory(organization=diff_organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(diff_dataset),
            object_id=diff_dataset.pk,
            dataset=diff_dataset,
            name="datasets/gov/org/dataset",
        )
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset1, dataset2, diff_dataset])
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]
        form["form-0-scopes"] = [
            "test_dataset1_getall",
            "test_dataset2_search",
            "test_dataset2_select",
        ]
        form["form-1-scopes"] = ["datasets_gov_org_dataset_getall"]
        response = form.submit()

        assert response.status_code == 302
        assert response.url == reverse("project-detail", args=[project.pk])

        assert Agreement.objects.filter(project=project).count() == 2
        assert set(
            AgreementScope.objects.filter(
                agreement__assigner_organization=organization
            ).values_list("resource", flat=True)
        ) == {"test_dataset1_getall", "test_dataset2_search", "test_dataset2_select"}
        assert set(
            AgreementScope.objects.filter(
                agreement__assigner_organization=diff_organization
            ).values_list("resource", flat=True)
        ) == {"datasets_gov_org_dataset_getall"}

    def test_cannot_create_agreement_with_invalid_scopes(
        self, app: DjangoTestApp
    ) -> None:
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            dataset=dataset,
            name="test/dataset",
        )
        user = UserFactory(organization=organization)
        project = ProjectFactory(user=user, datasets=[dataset])
        app.set_user(user)

        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-id": organization.id,
            "form-0-scopes": ["bad_scope"],
        }
        response = app.post(reverse("agreement-create", args=[project.pk]), data)

        assert response.status_code == 200
        assert Agreement.objects.filter(project=project).count() == 0
