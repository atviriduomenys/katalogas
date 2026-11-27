"""Agreements can grant a model's scopes (`Model/@scope`), which limit the rows and columns a client gets (#2877)."""

import csv
import io

import pytest
import requests_mock
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from factory.django import FileField

from tests.projects.test_views import mock_oauth_endpoints, oauth_settings  # noqa: F401
from vitrina.cms.factories import FilerFileFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.datasets.structure import HEADER
from vitrina.orgs.factories import ViispRepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory, UseCaseClientFactory
from vitrina.projects.models import UseCaseClientScope
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.smart_contracts.forms import SmartContractForm
from vitrina.smart_contracts.models import AgreementScope
from vitrina.structure.factories import MetadataFactory, ModelFactory, ModelScopeFactory, PropertyFactory
from vitrina.structure.models import Model, ModelScope, Property
from vitrina.structure.services import create_structure_objects
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def _model(dataset: Dataset, name: str) -> Model:
    version = dataset.latest_version()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=model.pk,
        dataset=dataset,
        name=f"{dataset.name}/{name}",
        metadata_version=version,
    )
    return model


def _scope(model: Model, name: str) -> None:
    scope = ModelScopeFactory(model=model, metadata_version=model.metadata_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(ModelScope),
        object_id=scope.pk,
        dataset=model.dataset,
        ref=name,
        prepare="code='lt'",
        metadata_version=model.metadata_version,
    )


def test_scope_choices_include_the_models_scopes(organization: Organization, dataset: Dataset):
    _scope(_model(dataset, "City"), "ltu")

    form = SmartContractForm(
        instance=organization, dataset_metadata_by_organization={organization.id: [dataset.metadata.first()]}
    )

    assert {value for value, _ in form.fields["scopes"].choices} == {
        "uapi:/test/dataset/:getall",
        "uapi:/test/dataset/:getone",
        "uapi:/test/dataset/:search",
        "uapi:/test/dataset/City/@ltu/:getall",
        "uapi:/test/dataset/City/@ltu/:getone",
        "uapi:/test/dataset/City/@ltu/:search",
    }


def test_agreement_grants_a_model_scope(app: DjangoTestApp, organization: Organization, dataset: Dataset):
    _scope(_model(dataset, "City"), "ltu")
    representative = ViispRepresentativeFactory(content_object=organization, can_make_agreements=True)
    project = ProjectFactory(datasets=[dataset], organization=organization)
    app.set_user(representative.user)

    form = app.get(reverse("project-agreement-create", args=[project.pk])).forms["project-agreement-create"]
    form["form-0-scopes"] = ["uapi:/test/dataset/City/@ltu/:getall"]
    form.submit()

    scope = AgreementScope.objects.get(agreement__project=project)
    assert (scope.scope, scope.resource, scope.action) == (
        "uapi:/test/dataset/City/@ltu/:getall",
        "uapi:/test/dataset/City/@ltu",
        "getall",
    )


def test_client_gets_a_model_scope_from_an_active_agreement(app: DjangoTestApp, oauth_settings, organization):  # noqa: F811
    with requests_mock.Mocker() as oauth:
        mock_oauth_endpoints(oauth, oauth_settings)
        representative = ViispRepresentativeFactory()
        app.set_user(representative.user)
        project = ProjectFactory(organization=representative.content_object)
        client = UseCaseClientFactory(use_case=project)
        agreement = AgreementFactory(project=project, assigner=organization, status=AgreementStatuses.ACTIVE)
        scope = agreement.scopes.create(
            scope="uapi:/test/dataset/City/@ltu/:getall", resource="uapi:/test/dataset/City/@ltu", action="getall"
        )

        form = app.get(reverse("project-clients-scopes-create", args=[project.pk, client.pk])).forms[
            "client-scope-form"
        ]
        form["scope"] = scope.pk
        form.submit()

    assert UseCaseClientScope.objects.get(use_case_client=client).scope == "uapi:/test/dataset/City/@ltu/:getall"


def test_scope_cannot_have_a_property_name(app: DjangoTestApp):
    dataset = DatasetFactory(metadata="test/dataset")
    model = _model(dataset, "City")
    prop = PropertyFactory(model=model, metadata_version=model.metadata_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(Property),
        object_id=prop.pk,
        dataset=dataset,
        name="code",
        type="string",
        metadata_version=model.metadata_version,
    )
    app.set_user(UserFactory(is_staff=True))
    url = reverse("model-scope-create", args=[dataset.pk, model.metadata_version.pk, "City"])
    form = app.get(url).forms["property-form"]
    form["ref"] = "code"
    form["prepare"] = "code='lt'"

    resp = form.submit()

    assert resp.status_code == 200
    assert "ref" in resp.context["form"].errors
    assert model.model_scopes.count() == 0


def _import(dataset: Dataset, manifest: str) -> None:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=HEADER, restval="", lineterminator="\n")
    writer.writeheader()
    writer.writerows(csv.DictReader(io.StringIO(manifest)))
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=out.getvalue())), dataset=dataset
    )
    dataset.current_structure = structure
    dataset.save()
    create_structure_objects(structure)


def test_import_skips_a_scope_named_like_a_property_with_an_error_note():
    dataset = DatasetFactory(metadata="test/dataset")

    _import(
        dataset,
        "dataset,model,property,type,ref,prepare\n"
        "test/dataset,,,,,\n"
        ",City,,,,\n"
        ",,,scope,code,code='lt'\n"
        ",,,scope,ltu,code='lt'\n"
        ",,code,string,,\n",
    )

    model = Model.objects.get(dataset=dataset)
    assert [scope.metadata.first().ref for scope in model.model_scopes.all()] == ["ltu"]
    errors = Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model), object_id=model.pk, type=Comment.STRUCTURE_ERROR
    )
    assert any("code" in error.body for error in errors)
