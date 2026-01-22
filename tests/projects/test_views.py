import io
import uuid
from urllib.parse import parse_qs

import pytest
import requests_mock
import reversion
from PIL import Image
from django.urls import reverse, resolve
from django_webtest import DjangoTestApp
from reversion.models import Version
from webtest import Upload

from vitrina.datasets.factories import DatasetFactory
from vitrina.comments.models import Comment
from vitrina.projects.factories import ProjectFactory, UseCaseClientFactory, UseCaseClientScopeFactory
from vitrina.projects.models import Project, UseCaseClient, UseCaseClientScope
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory, AgreementPDFFileFactory
from vitrina.smart_contracts.models import AgreementScope
from vitrina.users.factories import UserFactory
from filer.models.imagemodels import Image as FilerImage
from vitrina.orgs.factories import OrganizationFactory, ViispRepresentativeFactory, RepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.users.models import User
from vitrina.utils import RevisionComment, RevisionSource

pytestmark = pytest.mark.django_db


def generate_photo_file() -> bytes:
    file = io.BytesIO()
    image = Image.new("RGBA", size=(100, 100), color=(155, 0, 0))
    image.save(file, "png")
    file.name = "example.png"
    return file.getvalue()


@pytest.mark.parametrize("is_public", [True, False])
def test_project_create_personal(app: DjangoTestApp, is_public: bool):
    user = UserFactory()
    app.set_user(user)

    url = reverse("project-create")
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW, action="project-create", http_method="POST", path=url, args=(), kwargs={}
    )
    form = app.get(url).forms["project-form"]
    form["title"] = "Project"
    form["description"] = "Description"
    form["url"] = "example.com"
    form["image"] = Upload("example.png", generate_photo_file(), "image")
    form["is_public"] = is_public
    resp = form.submit()

    project_qs = Project.objects.filter(title="Project")
    assert project_qs.exists()
    added_project = project_qs.first()
    assert resp.status_code == 302
    assert resp.url == added_project.get_absolute_url()
    assert Version.objects.get_for_object(added_project).count() == 1
    assert Version.objects.get_for_object(added_project).first().revision.comment == revision_comment.to_json()
    assert FilerImage.objects.count() == 1
    assert added_project.image.original_filename == "example.png"
    assert not added_project.organization
    assert added_project.is_public == is_public


def test_project_create_for_organization(app: DjangoTestApp):
    representative = ViispRepresentativeFactory(can_make_agreements=True)
    user = representative.user
    app.set_user(user)
    organization = representative.content_object

    url = reverse("project-create")
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW, action="project-create", http_method="POST", path=url, args=(), kwargs={}
    )
    form = app.get(url).forms["project-form"]
    form["title"] = "Project"
    form["description"] = "Description"
    form["organization"] = organization.id
    form["url"] = "example.com"
    form["image"] = Upload("example.png", generate_photo_file(), "image")
    resp = form.submit()

    added_project = Project.objects.filter(title="Project").first()
    assert added_project
    assert resp.status_code == 302
    assert resp.url == added_project.get_absolute_url()
    assert Version.objects.get_for_object(added_project).count() == 1
    assert Version.objects.get_for_object(added_project).first().revision.comment == revision_comment.to_json()
    assert FilerImage.objects.count() == 1
    assert added_project.image.original_filename == "example.png"
    assert added_project.organization == organization
    assert not added_project.is_public


def test_organization_project_create_viisp_no_representative(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
    app.set_user(user)

    form = app.get(reverse("project-create")).forms["project-form"]
    form["title"] = "Project"
    form["description"] = "Description"
    form["url"] = "example.com"
    form["image"] = Upload("example.png", generate_photo_file(), "image")
    assert "organization" not in form.fields

    resp = form.submit()

    assert resp.status_code == 302
    project = Project.objects.filter(title="Project").first()
    assert not project.organization


def test_organization_project_create_viisp_representative_no_agreements_flag(app: DjangoTestApp):
    representative = ViispRepresentativeFactory(can_make_agreements=False)
    user = representative.user
    app.set_user(user)

    form = app.get(reverse("project-create")).forms["project-form"]
    form["title"] = "Project"
    form["description"] = "Description"
    form["url"] = "example.com"
    form["image"] = Upload("example.png", generate_photo_file(), "image")
    assert "organization" not in form.fields


def test_personal_project_update(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(user=user)

    app.set_user(user)

    url = reverse("project-update", args=[project.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="project-update",
        http_method="POST",
        path=url,
        args=(),
        kwargs={"pk": project.pk},
    )
    form = app.get(url).forms["project-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    resp = form.submit()

    project.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == project.get_absolute_url()
    assert project.title == "Updated title"
    assert project.description == "Updated description"
    assert Version.objects.get_for_object(project).count() == 1
    assert Version.objects.get_for_object(project).first().revision.comment == revision_comment.to_json()


def test_organization_project_update_no_permission(app: DjangoTestApp):
    representative = ViispRepresentativeFactory(can_make_agreements=False)
    user = representative.user
    project = ProjectFactory(user=user, organization=representative.content_object)

    app.set_user(user)

    resp = app.get(reverse("project-update", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_personal_project_update_no_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory()

    app.set_user(user)

    resp = app.get(reverse("project-update", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_project_cannot_update_organization(app: DjangoTestApp):
    representative = ViispRepresentativeFactory(can_make_agreements=True)
    user = representative.user
    project = ProjectFactory(user=user, organization=representative.content_object)

    app.set_user(user)

    form = app.get(reverse("project-update", args=[project.pk])).forms["project-form"]
    assert "organization" not in form.fields


def test_project_update_with_agreements(app: DjangoTestApp, organization: Organization):
    user = UserFactory()
    RepresentativeFactory(user=user, content_object=organization)
    project = ProjectFactory(user=user, organization=organization)
    AgreementFactory(project=project)

    app.set_user(user)

    resp = app.get(reverse("project-update", args=[project.pk]))

    assert resp.status_code == 302


def test_project_update_with_organization(app: DjangoTestApp):
    representative = ViispRepresentativeFactory(can_make_agreements=True)
    user = representative.user
    app.set_user(user)
    organization = representative.content_object
    project = ProjectFactory(user=user, organization=organization)

    app.set_user(user)
    url = reverse("project-update", args=[project.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="project-update",
        http_method="POST",
        path=url,
        args=(),
        kwargs={"pk": project.pk},
    )
    form = app.get(url).forms["project-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    resp = form.submit()

    project.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == project.get_absolute_url()
    assert project.title == "Updated title"
    assert project.description == "Updated description"
    assert Version.objects.get_for_object(project).count() == 1
    assert Version.objects.get_for_object(project).first().revision.comment == revision_comment.to_json()


def test_project_update_with_organization_no_representative(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    project = ProjectFactory(user=user, organization=organization)

    app.set_user(user)

    resp = app.get(reverse("project-update", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_project_history_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory()
    app.set_user(user)
    resp = app.get(reverse("project-history", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_project_history_view_with_permission(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    app.set_user(user)

    url = reverse("project-update", args=[project.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="project-update",
        http_method="POST",
        path=url,
        args=(),
        kwargs={"pk": project.pk},
    )
    form = app.get(url).forms["project-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    resp = form.submit().follow()
    with reversion.create_revision():
        agreement_file = AgreementPDFFileFactory(agreement__project=project)
        scope = UseCaseClientScopeFactory(use_case_client__use_case=project)

    action_objects = [
        (str(agreement_file.agreement), None),
        (str(agreement_file), None),
        (str(scope.use_case_client), None),
        (str(scope), None),
    ]

    resp = resp.click(linkid="history-tab")
    project.refresh_from_db()
    assert resp.context["detail_url_name"] == "project-detail"
    assert resp.context["history_url_name"] == "project-history"
    assert len(resp.context["history"]) == 2

    entry1 = resp.context["history"][0]
    assert entry1["action"]["comment"] == ""
    assert len(entry1["action"]["objects"]) == 4
    assert set(entry1["action"]["objects"]) == set(action_objects)
    assert entry1["user"] is None

    entry2 = resp.context["history"][1]
    assert entry2["action"]["comment"] == f"{revision_comment.action}({revision_comment.kwargs})"
    assert len(entry2["action"]["objects"]) == 1
    assert entry2["action"]["objects"][0] == (str(project), project.get_absolute_url())
    assert entry2["user"] == user


def test_request_comment_with_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory(status=Project.CREATED)
    app.set_user(user)

    form = app.get(project.get_absolute_url()).forms["comment-form"]
    match = resolve(form.action)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW, action="comment", http_method="POST", path=form.action, args=(), kwargs=match.kwargs
    )
    form["is_public"] = True
    form["status"] = Comment.APPROVED
    form["body"] = "Approving this project"
    resp = form.submit().follow()

    comment = project.comments.get()
    assert comment in list(resp.context["comments"])[0]
    assert comment.type == Comment.STATUS
    assert comment.status == Comment.APPROVED

    version = Version.objects.get_for_object(project).get()
    assert version.revision.comment == revision_comment.to_json()


def test_request_comment_with_status_rejected(app: DjangoTestApp):
    project = ProjectFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(project.get_absolute_url()).forms["comment-form"]
    match = resolve(form.action)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW, action="comment", http_method="POST", path=form.action, args=(), kwargs=match.kwargs
    )
    form["is_public"] = True
    form["status"] = Comment.REJECTED
    form["body"] = ""
    resp = form.submit().follow()

    comment = project.comments.get()
    assert comment in list(resp.context["comments"])[0]
    assert comment.type == Comment.STATUS
    assert comment.status == Comment.REJECTED

    version = Version.objects.get_for_object(project).get()
    assert version.revision.comment == revision_comment.to_json()


def test_request_comment_with_same_status(app: DjangoTestApp):
    project = ProjectFactory(status=Project.APPROVED)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(project.get_absolute_url()).forms["comment-form"]
    form["status"] = Comment.APPROVED
    form.submit().follow()

    assert project.comments.count() == 0
    assert Version.objects.get_for_object(project).count() == 0


def test_remove_dataset_no_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory()
    dataset = DatasetFactory()
    project.datasets.add(dataset)
    assert project.datasets.all().count() == 1

    app.set_user(user)

    resp = app.get(
        reverse("project-dataset-remove", kwargs={"pk": project.pk, "dataset_id": dataset.pk}), expect_errors=True
    )

    assert resp.status_code == 403


def test_remove_dataset(app: DjangoTestApp) -> None:
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    project = ProjectFactory(datasets=[dataset])

    app.post(reverse("project-dataset-remove", kwargs={"pk": project.pk, "dataset_id": dataset.pk}))

    project.refresh_from_db()
    assert not project.datasets.exists()


def test_remove_dataset_with_permission(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    dataset = DatasetFactory()
    project.datasets.add(dataset)
    assert project.datasets.all().count() == 1

    url = reverse("project-datasets", kwargs={"pk": project.pk})
    app.set_user(user)

    resp = app.get(url)
    resp = resp.click(linkid=f"remove-dataset-{dataset.pk}-btn")

    form = resp.forms["delete-form"]
    resp = form.submit()

    assert resp.headers["location"] == url
    assert project.datasets.all().count() == 0


def test_not_approved_project_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(status=Project.CREATED)
    app.set_user(user)
    resp = app.get(reverse("project-detail", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_approved_non_public_project_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(status=Project.APPROVED, is_public=False)
    app.set_user(user)
    resp = app.get(reverse("project-detail", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_not_approved_project_view_with_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(user=user, status=Project.CREATED)
    app.set_user(user)

    resp = app.get(reverse("project-detail", args=[project.pk]))
    assert resp.context["object"] == project


@pytest.mark.parametrize(
    "project_status, is_public",
    [
        (Project.APPROVED, True),
        (Project.APPROVED, False),
        (Project.CREATED, True),
        (Project.CREATED, False),
        (Project.REJECTED, True),
        (Project.REJECTED, False),
    ],
)
def test_representative_can_view_any_organization_projects(app: DjangoTestApp, project_status, is_public: bool):
    organization = OrganizationFactory()
    user = UserFactory()
    RepresentativeFactory(user=user, content_object=organization)
    project = ProjectFactory(organization=organization, is_public=is_public, status=project_status)
    app.set_user(user)

    resp = app.get(reverse("project-detail", args=[project.pk]))
    assert resp.context["object"] == project


@pytest.mark.parametrize(
    "project_status, is_public",
    [
        (Project.APPROVED, False),
        (Project.CREATED, True),
        (Project.CREATED, False),
        (Project.REJECTED, True),
        (Project.REJECTED, False),
    ],
)
def test_non_representative_cannot_view_non_public_non_approved_organization_projects(
    app: DjangoTestApp, project_status, is_public: bool
):
    organization = OrganizationFactory()
    user = UserFactory()
    project = ProjectFactory(organization=organization, is_public=is_public, status=project_status)
    app.set_user(user)

    resp = app.get(reverse("project-detail", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "project_status, is_public",
    [
        (Project.APPROVED, True),
        (Project.APPROVED, False),
        (Project.CREATED, True),
        (Project.CREATED, False),
        (Project.REJECTED, True),
        (Project.REJECTED, False),
    ],
)
def test_user_can_view_any_personal_projects(app: DjangoTestApp, project_status, is_public: bool):
    user = UserFactory()
    project = ProjectFactory(user=user, is_public=is_public, status=project_status)
    app.set_user(user)

    resp = app.get(reverse("project-detail", args=[project.pk]))
    assert resp.context["object"] == project


@pytest.mark.parametrize(
    "project_status, is_public",
    [
        (Project.APPROVED, True),
        (Project.APPROVED, False),
        (Project.CREATED, True),
        (Project.CREATED, False),
        (Project.REJECTED, True),
        (Project.REJECTED, False),
    ],
)
def test_assigner_can_view_any_projects_it_is_part_of(app: DjangoTestApp, project_status, is_public: bool):
    organization = OrganizationFactory()
    dataset = DatasetFactory()
    user = UserFactory()
    RepresentativeFactory(user=user, content_object=dataset.organization)
    project = ProjectFactory(organization=organization, is_public=is_public, status=project_status)
    project.datasets.add(dataset)
    app.set_user(user)

    resp = app.get(reverse("project-detail", args=[project.pk]))
    assert resp.context["object"] == project


def test_clients_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(user=user)
    app.set_user(user)
    resp = app.get(reverse("project-clients", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_clients_view(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory()
    RepresentativeFactory(user=user, content_object=organization)
    project = ProjectFactory(user=user, organization=organization)
    UseCaseClientFactory.create_batch(2, use_case=project)
    app.set_user(user)
    resp = app.get(reverse("project-clients", args=[project.pk]))
    assert resp.status_code == 200
    assert project.client_set.count() == 2
    assert resp.context["clients"].count() == 2


def test_client_create_without_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory()
    RepresentativeFactory(user=user, content_object=organization)
    app.set_user(user)
    project = ProjectFactory(user=user, organization=organization)

    resp = app.get(reverse("project-clients-create", args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_client_create(app: DjangoTestApp, oauth_settings):
    new_client_id = str(uuid.uuid4())

    with requests_mock.Mocker() as m:
        # Mock OAuth token request
        m.post(
            oauth_settings.OAUTH_SERVER_TOKEN_URL,
            json={"access_token": "token_to_create_clients"},
            status_code=201,
        )

        # Mock client creation request
        def create_client_callback(request, context):
            context.status_code = 201
            # Return a JSON that includes client_id
            return {"client_id": new_client_id}

        m.post(oauth_settings.OAUTH_SERVER_CLIENTS_URL, json=create_client_callback)

        representative = ViispRepresentativeFactory()
        user = representative.user
        app.set_user(user)
        project: Project = ProjectFactory(organization=representative.content_object)

        form = app.get(reverse("project-clients-create", args=[project.pk])).forms["client-form"]
        form["name"] = "Client"
        resp = form.submit()

        added_client: UseCaseClient = UseCaseClient.objects.filter(name="Client").first()
        assert added_client
        assert added_client.client_id == new_client_id
        assert resp.status_code == 302

        # --- Assertions for correct OAuth requests ---
        # Access token POST
        token_requests = [
            req
            for req in m.request_history
            if req.method == "POST" and req.url == oauth_settings.OAUTH_SERVER_TOKEN_URL
        ]
        assert token_requests, "No access token request made"
        token_data = parse_qs(token_requests[0].text)
        assert token_data.get("grant_type") == ["client_credentials"]
        assert token_data.get("scope") == [oauth_settings.OAUTH_CLIENTS_MANAGEMENT_SCOPE]

        # Client creation POST
        client_requests = [
            req
            for req in m.request_history
            if req.method == "POST" and req.url == oauth_settings.OAUTH_SERVER_CLIENTS_URL
        ]
        assert client_requests, "No client creation request made"
        client_json = client_requests[0].json()
        assert "secret" in client_json
        assert "client_name" in client_json
        assert "scopes" in client_json


def test_client_update_without_permission(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory()
    RepresentativeFactory(user=user, content_object=organization)
    app.set_user(user)
    project = ProjectFactory(user=user, organization=organization)
    client = UseCaseClientFactory(use_case=project)
    resp = app.get(reverse("project-clients-update", args=[project.pk, client.uuid]), expect_errors=True)
    assert resp.status_code == 403


def test_client_update(app: DjangoTestApp, oauth_settings):
    with requests_mock.Mocker() as m:
        mock_oauth_endpoints(m, oauth_settings)

        representative = ViispRepresentativeFactory()
        user = representative.user
        app.set_user(user)
        project = ProjectFactory(organization=representative.content_object)
        client = UseCaseClientFactory()

        form = app.get(reverse("project-clients-update", args=[project.pk, client.uuid])).forms["client-form"]
        form["name"] = "Client"
        resp = form.submit()

        added_client = UseCaseClient.objects.filter(name="Client")
        clients = UseCaseClient.objects.all()

        assert clients.count() == 1
        assert added_client.exists()
        assert resp.status_code == 302
        assert not m.called  # Should not hit remote endpoints


def test_client_scope_create(app: DjangoTestApp, oauth_settings, organization):
    with requests_mock.Mocker() as m:
        mock_oauth_endpoints(m, oauth_settings)
        representative = ViispRepresentativeFactory()
        user: User = representative.user
        app.set_user(user)
        project = ProjectFactory(organization=representative.content_object)
        client: UseCaseClient = UseCaseClientFactory(use_case=project)
        agreement = AgreementFactory(project=project, assigner=organization, status=AgreementStatuses.ACTIVE)
        available_scope: AgreementScope = agreement.scopes.create(scope="Test", action="WRITE", resource="dataset")

        url = reverse("project-clients-scopes-create", args=[project.pk, client.pk])
        resp = app.get(url)
        assert resp.status_code == 200

        form = resp.forms["client-scope-form"]
        form["scope"] = available_scope.pk
        response = form.submit()

        created_scope = UseCaseClientScope.objects.filter(use_case_client=client).first()

        assert created_scope
        assert created_scope.is_active is False
        assert response.status_code == 302
        assert not m.called  # No OAuth requests should be made


def test_client_scope_toggle(app: DjangoTestApp, oauth_settings):
    with requests_mock.Mocker() as m:
        mock_oauth_endpoints(m, oauth_settings)

        representative = ViispRepresentativeFactory()
        user: User = representative.user
        app.set_user(user)
        project = ProjectFactory(organization=representative.content_object)
        client: UseCaseClient = UseCaseClientFactory(use_case=project)
        scope = client.scopes.create(scope="Test", action="WRITE", resource="dataset")

        url = reverse("project-clients-scopes-detail-toggle", args=[project.pk, client.pk, scope.pk])
        resp = app.post(url)

        assert resp.status_code == 302

        updated_scope = UseCaseClientScope.objects.filter(use_case_client=client).first()
        assert updated_scope
        assert updated_scope.is_active is True

        patch_requests = [req for req in m.request_history if req.method == "PATCH"]
        assert patch_requests, "No PATCH request made"
        patch_req = patch_requests[0]

        expected_url = f"{oauth_settings.OAUTH_SERVER_CLIENTS_URL}/{client.client_id}"
        assert patch_req.url == expected_url, f"PATCH called to wrong URL: {patch_req.url}"

        patch_json = patch_req.json()
        assert "scopes" in patch_json
        post_requests = [req for req in m.request_history if req.method == "POST"]
        assert post_requests, "No POST request made"
        post_req = post_requests[0]
        assert post_req.url == oauth_settings.OAUTH_SERVER_TOKEN_URL

        data = parse_qs(post_req.text)
        assert data.get("grant_type") == ["client_credentials"]
        assert data.get("scope") == [oauth_settings.OAUTH_CLIENTS_MANAGEMENT_SCOPE]


@pytest.fixture
def oauth_settings(settings):
    settings.OAUTH_SERVER_TOKEN_URL = "https://oauth.test/token"
    settings.OAUTH_SERVER_CLIENTS_URL = "https://oauth.test/clients"
    settings.OAUTH_CLIENT_SECRET_BASE64 = "ZmFrZV9iYXNlNjRfY2xpZW50X3NlY3JldA=="
    settings.OAUTH_CLIENTS_MANAGEMENT_SCOPE = "auth_clients"
    return settings


def mock_oauth_endpoints(m, settings):
    m.post(
        settings.OAUTH_SERVER_TOKEN_URL,
        json={"access_token": "token_to_create_clients"},
        status_code=201,
    )
    m.post(
        settings.OAUTH_SERVER_CLIENTS_URL,
        json={"client_id": "mock-client-id"},
        status_code=201,
    )
    m.patch(
        requests_mock.ANY,
        json={},
        status_code=200,
    )
