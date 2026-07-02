import pytest
from django.contrib.admin import AdminSite
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.urls import reverse
from django.utils.html import escape

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.admin import RepresentativeRequestAdmin
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization, Representative, RepresentativeRequest
from vitrina.users.factories import UserFactory

from vitrina.users.models import User


@pytest.mark.django_db
def test_admin_add_publisher(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    organization = OrganizationFactory()
    app.set_user(admin)
    form = app.get(reverse("admin:vitrina_orgs_publisherorganization_add")).forms["publisherorganization_form"]
    form["organization"] = organization.pk
    form.submit()
    assert Organization.objects.filter(publisher=True, pk=organization.pk).exists()


@pytest.mark.django_db
def test_admin_publisher_list_display(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    org = OrganizationFactory(title="title")
    for title in ["title1", "title2", "title3"]:
        OrganizationFactory(title=title, publisher=True)
    app.set_user(admin)
    resp = app.get(reverse("admin:vitrina_orgs_publisherorganization_changelist"))
    assert [org.title for org in resp.context["cl"].result_list] == ["title1", "title2", "title3"]
    assert org.title not in [org.title for org in resp.context["cl"].result_list]


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(email="admin@gmail.com", password="test123")


@pytest.fixture
def publisher_org():
    return OrganizationFactory(publisher=True)


@pytest.fixture
def creator_org():
    return OrganizationFactory(publisher=False)


@pytest.mark.django_db
def test_admin_dataset_assign(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    datasets = [DatasetFactory() for _ in range(3)]

    app.set_user(admin_user)
    form = app.get(reverse("admin:vitrina_orgs_publisherorganization_change", args=[publisher_org.pk])).forms[
        "publisherorganization_form"
    ]

    form["datasets"] = [str(dataset.id) for dataset in datasets]
    response = form.submit()

    assert response.status_code == 302
    for dataset in datasets:
        assert Representative.objects.filter(
            organization=publisher_org, content_type=ContentType.objects.get_for_model(Dataset), object_id=dataset.id
        ).exists()


@pytest.mark.django_db
def test_admin_dataset_remove(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    datasets = [DatasetFactory() for _ in range(3)]
    app.set_user(admin_user)
    for dataset in datasets:
        Representative.objects.create(
            organization=publisher_org, content_type=ContentType.objects.get_for_model(Dataset), object_id=dataset.id
        )
    form = app.get(reverse("admin:vitrina_orgs_publisherorganization_change", args=[publisher_org.pk])).forms[
        "publisherorganization_form"
    ]
    form["datasets"] = [str(datasets[0].id), str(datasets[1].id)]
    response = form.submit()
    assert response.status_code == 302

    assert not Representative.objects.filter(
        organization=publisher_org, content_type=ContentType.objects.get_for_model(Dataset), object_id=datasets[2].id
    ).exists()

    for dataset in datasets[:2]:
        assert Representative.objects.filter(
            organization=publisher_org, content_type=ContentType.objects.get_for_model(Dataset), object_id=dataset.id
        ).exists()


@pytest.mark.django_db
def test_admin_organization_assign(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    orgs = [OrganizationFactory() for _ in range(3)]

    app.set_user(admin_user)
    form = app.get(reverse("admin:vitrina_orgs_publisherorganization_change", args=[publisher_org.pk])).forms[
        "publisherorganization_form"
    ]

    form["creator_assignment"] = [str(org.id) for org in orgs]
    response = form.submit()

    assert response.status_code == 302
    for org in orgs:
        assert Representative.objects.filter(
            organization=publisher_org, content_type=ContentType.objects.get_for_model(Organization), object_id=org.id
        ).exists()


@pytest.mark.django_db
def test_admin_organization_remove(app: DjangoTestApp, admin_user: User, publisher_org: Organization):
    orgs = [OrganizationFactory() for _ in range(3)]
    app.set_user(admin_user)
    for org in orgs:
        Representative.objects.create(
            organization=publisher_org, content_type=ContentType.objects.get_for_model(Organization), object_id=org.id
        )
    form = app.get(reverse("admin:vitrina_orgs_publisherorganization_change", args=[publisher_org.pk])).forms[
        "publisherorganization_form"
    ]
    form["creator_assignment"] = [str(orgs[0].id), str(orgs[1].id)]
    response = form.submit()
    assert response.status_code == 302

    assert not Representative.objects.filter(
        organization=publisher_org, content_type=ContentType.objects.get_for_model(Organization), object_id=orgs[2].id
    ).exists()


@pytest.mark.django_db
def test_response_change_flash_message_escapes_user_name():
    xss_payload = "<script>alert('xss')</script>"

    user = UserFactory()
    user.first_name = xss_payload
    user.save()

    org = OrganizationFactory()
    rep_request = RepresentativeRequest.objects.create(
        user=user,
        organization=org,
        status=RepresentativeRequest.CREATED,
    )

    request = RequestFactory().post("/")
    request.user = user
    setattr(request, "session", "session")
    storage = FallbackStorage(request)
    setattr(request, "_messages", storage)

    admin = RepresentativeRequestAdmin(RepresentativeRequest, AdminSite())
    admin.response_change(request, rep_request)

    messages = [str(m) for m in get_messages(request)]
    assert messages, "Expected a flash message"
    assert xss_payload not in messages[0]
    assert escape(xss_payload) in messages[0]
