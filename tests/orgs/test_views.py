import io
import json
from pathlib import Path
from unittest.mock import patch, Mock
from bs4 import BeautifulSoup
import pytest
from datetime import datetime, timedelta

from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from django_recaptcha.client import RecaptchaResponse
from freezegun import freeze_time
import pytz
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse
from django_webtest import DjangoTestApp
from itsdangerous import URLSafeSerializer
from pdfminer.high_level import extract_text
from webtest import Upload

from vitrina.api.factories import APIKeyFactory
from vitrina.api.models import ApiKey
from vitrina.classifiers.factories import AreaOfManagementFactory
from vitrina.classifiers.models import AreaOfManagement
from vitrina.datasets.factories import DatasetFactory, ContactFactory
from vitrina.datasets.models import Contact, Dataset
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory, ViispRepresentativeFactory
from vitrina.orgs.models import Representative, Organization
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory, AgreementPDFFileFactory, AgreementJSONFileFactory
from vitrina.smart_contracts.models import SmartContractTemplate
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


pytestmark = pytest.mark.django_db
timezone = pytz.timezone(settings.TIME_ZONE)


def test_organization_detail_tab(app: DjangoTestApp):
    parent_organization = OrganizationFactory()
    organization = parent_organization.add_child(instance=OrganizationFactory.build())
    resp = app.get(organization.get_absolute_url())
    assert list(resp.context["ancestors"]) == [parent_organization]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Informacija"]


def test_organization_members_tab(app: DjangoTestApp):
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    content_type = ContentType.objects.get_for_model(Organization)
    representative1 = RepresentativeFactory(
        content_type=content_type,
        object_id=organization1.pk,
    )
    RepresentativeFactory(
        content_type=content_type,
        object_id=organization2.pk,
    )
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    app.set_user(admin)
    resp = app.get(reverse("organization-members", args=[organization1.pk]))
    assert list(resp.context["members"]) == [representative1]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == [
        "Tvarkytojai",
    ]


@pytest.mark.haystack
def test_organization_dataset_tab(app: DjangoTestApp):
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    dataset1 = DatasetFactory(organization=organization1)
    DatasetFactory(organization=organization2)
    resp = app.get(reverse("organization-datasets", args=[organization1.pk]))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [dataset1.pk]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Duomenų ištekliai"]


@pytest.fixture
def organizations():
    with freeze_time(timezone.localize(datetime(2022, 8, 22, 10, 30))):
        organization1 = OrganizationFactory(
            slug="org1",
            title="Organization 1",
            jurisdiction=AreaOfManagement.objects.get(id=1),
        )
    with freeze_time(timezone.localize(datetime(2022, 10, 22, 10, 30))):
        jurisdiction2 = AreaOfManagementFactory(id=30)
        organization2 = OrganizationFactory(slug="org2", title="Organization 2", jurisdiction=jurisdiction2)
    with freeze_time(datetime(2022, 9, 22, 10, 30)):
        organization3 = OrganizationFactory(
            slug="org3",
            title="Organization 3",
            jurisdiction=jurisdiction2,
        )
    return [organization1, organization2, organization3]


@pytest.mark.haystack
def test_search_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse("organization-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        organizations[0].pk,
        organizations[1].pk,
        organizations[2].pk,
    ]


def test_search_with_query_that_doesnt_match(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse("organization-list"), "doesnt-match"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == []


@pytest.mark.haystack
def test_search_with_query_that_matches_one(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse("organization-list"), "1"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [organizations[0].pk]


@pytest.mark.haystack
def test_search_with_query_that_matches_all(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse("organization-list"), "organization"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        organizations[0].pk,
        organizations[1].pk,
        organizations[2].pk,
    ]


@pytest.mark.haystack
def test_filter_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse("organization-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        organizations[0].pk,
        organizations[1].pk,
        organizations[2].pk,
    ]
    assert resp.context["selected_jurisdiction"] is None
    assert resp.context["jurisdictions"] == [
        {"id": 30, "title": "Jurisdiction30", "query": "?jurisdiction=30", "count": 2},
        {"id": 1, "title": "Nepriskirta", "query": "?jurisdiction=1", "count": 1},
    ]


@pytest.mark.haystack
def test_filter_with_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=1" % reverse("organization-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [organizations[0].pk]
    assert resp.context["selected_jurisdiction"] == "Nepriskirta"
    assert resp.context["jurisdictions"] == [{"id": 1, "title": "Nepriskirta", "query": "?jurisdiction=1", "count": 1}]


@pytest.mark.haystack
def test_filter_with_other_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=30" % reverse("organization-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [organizations[1].pk, organizations[2].pk]
    assert resp.context["selected_jurisdiction"] == "Jurisdiction30"
    assert resp.context["jurisdictions"] == [
        {"id": 30, "title": "Jurisdiction30", "query": "?jurisdiction=30", "count": 2}
    ]


@pytest.mark.haystack
def test_filter_with_non_existent_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=0" % reverse("organization-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == []
    assert resp.context["selected_jurisdiction"] is None
    assert resp.context["jurisdictions"] == []


@pytest.mark.haystack
def test_filter_with_jurisdiction_and_title(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=2&jurisdiction=30" % reverse("organization-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [organizations[1].pk]
    assert resp.context["selected_jurisdiction"] == "Jurisdiction30"
    assert resp.context["jurisdictions"] == [
        {"id": 30, "title": "Jurisdiction30", "query": "?q=2&jurisdiction=30", "count": 1},
    ]


@pytest.mark.haystack
def test_filter_with_query_containing_special_characters(app: DjangoTestApp):
    jurisdiction = AreaOfManagementFactory(id=30, name_lt="Jurisdiction\"<'>\\", name_en="Jurisdiction\"<'>\\")
    organization = OrganizationFactory(title="Organization \"<'>\\", jurisdiction=jurisdiction)
    resp = app.get("%s?q=\"<'>\\&jurisdiction=30" % reverse("organization-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [organization.pk]
    assert resp.context["selected_jurisdiction"] == "Jurisdiction\"<'>\\"
    assert resp.context["jurisdictions"] == [
        {"id": 30, "title": "Jurisdiction\"<'>\\", "query": "?q=\"<'>\\&jurisdiction=30", "count": 1},
    ]


@pytest.fixture
def representative_data():
    open_data_manager = User.objects.create_user(
        email="manager@gmail.com", password="manager123", first_name="Manager", last_name="User", phone="861234567"
    )
    resource_manager = User.objects.create_user(
        email="resource_manager@gmail.com",
        password="manager123",
        first_name="Manager",
        last_name="User",
        phone="861234567",
    )
    open_data_coordinator = User.objects.create_user(
        email="coordinator@gmail.com",
        password="coordinator123",
        first_name="Coordinator",
        last_name="User",
        phone="869876543",
    )
    resource_coordinator = User.objects.create_user(
        email="resource_coordinator@gmail.com",
        password="coordinator123",
        first_name="Coordinator",
        last_name="User",
        phone="869876543",
    )
    organization = OrganizationFactory()
    viisp_coordinator = User.objects.create_user(
        email="viispcoordinator@gmail.com",
        password="coordinator123",
        first_name="Viisp Coordinator",
        last_name="User",
        phone="869876543",
        is_viisp_login=True,
        viisp_company_code=organization.company_code,
    )
    content_type = ContentType.objects.get_for_model(Organization)
    open_data_representative_manager = RepresentativeFactory(
        role="open_data_manager", content_type=content_type, object_id=organization.pk
    )
    resource_representative_manager = RepresentativeFactory(
        role="resource_manager", content_type=content_type, object_id=organization.pk
    )
    open_data_representative_coordinator = RepresentativeFactory(
        role="open_data_coordinator", content_type=content_type, object_id=organization.pk, user=open_data_coordinator
    )
    resource_representative_coordinator = RepresentativeFactory(
        role="resource_coordinator", content_type=content_type, object_id=organization.pk, user=resource_coordinator
    )
    representative_viisp_coordinator = RepresentativeFactory(
        role="resource_coordinator", content_type=content_type, object_id=organization.pk, user=viisp_coordinator
    )
    return {
        "open_data_manager": open_data_manager,
        "resource_manager": resource_manager,
        "open_data_coordinator": open_data_coordinator,
        "resource_coordinator": resource_coordinator,
        "viisp_coordinator": viisp_coordinator,
        "organization": organization,
        "open_data_representative_manager": open_data_representative_manager,
        "resource_representative_manager": resource_representative_manager,
        "open_data_representative_coordinator": open_data_representative_coordinator,
        "resource_representative_coordinator": resource_representative_coordinator,
        "representative_viisp_coordinator": representative_viisp_coordinator,
        "content_type": content_type,
    }


def test_representative_create_without_permission(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_manager"])
    resp = app.get(
        reverse("representative-create", kwargs={"pk": representative_data["organization"].pk}), expect_errors=True
    )
    assert resp.status_code == 403


def test_representative_create_with_existing_user(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = "manager@gmail.com"
    form["role"] = "open_data_coordinator"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse("organization-members", kwargs={"pk": representative_data["organization"].pk})
    assert Representative.objects.filter(email="manager@gmail.com").count() == 1
    assert (
        Representative.objects.filter(email="manager@gmail.com").first().content_object
        == representative_data["organization"]
    )
    assert (
        Representative.objects.filter(email="manager@gmail.com").first().user
        == representative_data["open_data_manager"]
    )
    assert (
        Representative.objects.filter(email="manager@gmail.com").first().user.organization
        == representative_data["organization"]
    )


def test_representative_create_can_make_agreements_disabled(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    assert "disabled" in form["can_make_agreements"].attrs
    form["email"] = "manager@gmail.com"
    form["role"] = "open_data_coordinator"
    form["can_make_agreements"] = True
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse("organization-members", kwargs={"pk": representative_data["organization"].pk})
    representative_qs = Representative.objects.filter(email="manager@gmail.com")
    assert representative_qs.count() == 1
    representative = representative_qs.first()
    assert representative.content_object == representative_data["organization"]
    assert representative.user == representative_data["open_data_manager"]
    assert representative.user.organization == representative_data["organization"]
    assert not representative.can_make_agreements


def test_representative_create_with_can_make_agreements_rights(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["viisp_coordinator"])
    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = "manager@gmail.com"
    form["role"] = "open_data_coordinator"
    form["can_make_agreements"] = True
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse("organization-members", kwargs={"pk": representative_data["organization"].pk})
    representative_qs = Representative.objects.filter(email="manager@gmail.com")
    assert representative_qs.count() == 1
    representative = representative_qs.first()
    assert representative.content_object == representative_data["organization"]
    assert representative.user == representative_data["open_data_manager"]
    assert representative.user.organization == representative_data["organization"]
    assert representative.can_make_agreements


def test_representative_create_without_user(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = "new@gmail.com"
    form["role"] = "open_data_manager"
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse("organization-members", kwargs={"pk": representative_data["organization"].pk})
    assert Representative.objects.filter(email="new@gmail.com").count() == 1
    assert (
        Representative.objects.filter(email="new@gmail.com").first().content_object
        == representative_data["organization"]
    )
    assert Representative.objects.filter(email="new@gmail.com").first().user is None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@gmail.com"]


def test_representative_create_without_user_for_two_organizations(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    app.set_user(user)

    form = app.get(reverse("representative-create", kwargs={"pk": organization1.pk})).forms["representative-form"]
    form["email"] = "new@gmail.com"
    form["role"] = "open_data_manager"
    form.submit()

    form = app.get(reverse("representative-create", kwargs={"pk": organization2.pk})).forms["representative-form"]
    form["email"] = "new@gmail.com"
    form["role"] = "open_data_manager"
    form.submit()

    assert Representative.objects.filter(email="new@gmail.com").count() == 2
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@gmail.com"]


def test_representative_create_organization_as_representative(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["resource_coordinator"])
    organization1 = OrganizationFactory(email="test_org1@test.com")

    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = organization1.email
    form["role"] = "resource_manager"
    response = form.submit()
    assert response.status_code == 302
    representative_qs = Representative.objects.filter(email="test_org1@test.com")
    assert representative_qs.count() == 1
    assert representative_qs.first().role == "resource_manager"
    assert representative_qs.first().organization == organization1


@pytest.mark.parametrize(
    "representative_role",
    ["resource_coordinator", "open_data_coordinator"],
)
def test_representative_create_organization_as_coordinator_role(
    app: DjangoTestApp, representative_data, representative_role
):
    app.set_user(representative_data[representative_role])
    organization1 = OrganizationFactory(email="test_org1@test.com")

    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = organization1.email
    form["role"] = representative_role
    response = form.submit()
    assert response.status_code == 200
    assert "Organizacijai gali būti suteikta tik tvarkytojo rolė" in response.context["form"].errors["role"][0]
    assert Representative.objects.filter(email="test_org1@test.com").count() == 0


@pytest.mark.parametrize("restricted_role", ["resource_manager", "resource_coordinator"])
def test_open_data_coordinator_cannot_see_restricted_roles(app: DjangoTestApp, representative_data, restricted_role):
    app.set_user(representative_data["open_data_coordinator"])

    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]

    available_roles = [value for value, _, _ in form["role"].options]

    assert restricted_role not in available_roles


def test_representative_create_invalid_phone(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = "new@gmail.com"
    form["role"] = "open_data_manager"
    form["phone"] = "123456"
    resp = form.submit()
    assert resp.status_code == 200
    assert "Primtini formatai: +3706XXXXXXX, 0XXXXXXXX)" in resp.context["form"].errors["phone"][0]
    assert Representative.objects.filter(email="new@gmail.com").count() == 0


def test_representative_create_valid_phone(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_coordinator"])

    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = "new1@gmail.com"
    form["role"] = "open_data_manager"
    form["phone"] = "+37061234567"
    resp = form.submit()
    assert resp.status_code == 302
    rep_queryset = Representative.objects.filter(email="new1@gmail.com")
    assert rep_queryset.count() == 1
    assert rep_queryset.first().phone == "+37061234567"

    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = "new2@gmail.com"
    form["role"] = "open_data_manager"
    form["phone"] = "061234567"
    resp = form.submit()
    assert resp.status_code == 302
    rep_queryset = Representative.objects.filter(email="new2@gmail.com")
    assert rep_queryset.count() == 1
    assert rep_queryset.first().phone == "061234567"


def test_representative_update_phone(app: DjangoTestApp, representative_data):
    representative_data["open_data_representative_manager"].user = representative_data["open_data_manager"]
    representative_data["open_data_representative_manager"].save()
    app.set_user(representative_data["open_data_coordinator"])
    form = app.get(
        reverse(
            "representative-update",
            kwargs={
                "pk": representative_data["organization"].pk,
                "representative_id": representative_data["open_data_representative_manager"].pk,
            },
        )
    ).forms["representative-form"]
    form["phone"] = "061234567"
    resp = form.submit()
    assert resp.status_code == 302
    representative_data["open_data_representative_manager"].refresh_from_db()
    assert representative_data["open_data_representative_manager"].phone == "061234567"


def test_representative_update_organization_as_representative(app: DjangoTestApp, representative_data):
    organization_representative = OrganizationFactory(email="test_org1@test.com")
    organization_representative = RepresentativeFactory(
        role="resource_manager",
        content_type=representative_data["content_type"],
        object_id=representative_data["organization"].pk,
        organization=organization_representative,
    )
    organization_representative.save()
    app.set_user(representative_data["resource_coordinator"])
    form = app.get(
        reverse(
            "representative-update",
            kwargs={
                "pk": representative_data["organization"].pk,
                "representative_id": organization_representative.pk,
            },
        )
    ).forms["representative-form"]
    form["phone"] = "061234567"
    form["role"] = "open_data_manager"
    resp = form.submit()
    assert resp.status_code == 302
    organization_representative.refresh_from_db()
    assert organization_representative.phone == "061234567"
    assert organization_representative.role == "open_data_manager"


def test_representative_subscription(app: DjangoTestApp, representative_data):
    subscriptions_before = Subscription.objects.all()
    assert len(subscriptions_before) == 0

    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse("representative-create", kwargs={"pk": representative_data["organization"].pk})).forms[
        "representative-form"
    ]
    form["email"] = "manager@gmail.com"
    form["role"] = "open_data_manager"
    form["subscribe"] = True
    resp = form.submit()

    assert resp.status_code == 302
    assert resp.url == reverse("organization-members", kwargs={"pk": representative_data["organization"].pk})
    assert Representative.objects.filter(email="manager@gmail.com").count() == 1
    assert (
        Representative.objects.filter(email="manager@gmail.com").first().content_object
        == representative_data["organization"]
    )
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["manager@gmail.com"]

    subscription = Subscription.objects.get(user=representative_data["open_data_manager"])
    assert subscription.sub_type == Subscription.ORGANIZATION


def test_register_after_adding_representative(app: DjangoTestApp, representative_data):
    new_representative = RepresentativeFactory(
        email="new@gmail.com",
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=representative_data["organization"].pk,
        user=None,
    )
    serializer = URLSafeSerializer(settings.SECRET_KEY)
    token = serializer.dumps({"representative_id": new_representative.pk})

    with patch("django_recaptcha.fields.client.submit") as mocked_submit:
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        resp = app.post(
            reverse("representative-register", kwargs={"token": token}),
            {
                "first_name": "New",
                "last_name": "User",
                "email": "new@gmail.com",
                "password1": "v)Yxu*DF8}rj~(Sz!-X:Ws",
                "password2": "v)Yxu*DF8}rj~(Sz!-X:Ws",
                "agree_to_terms": True,
                "g-recaptcha-response": "PASSED",
            },
        )
        new_representative.refresh_from_db()
        assert resp.status_code == 302
        assert resp.url == reverse("home")
        assert User.objects.filter(email="new@gmail.com").count() == 1
        assert new_representative.user == User.objects.filter(email="new@gmail.com").first()
        assert new_representative.user.organization == representative_data["organization"]


def test_representative_update_without_permission(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_manager"])
    resp = app.get(
        reverse("representative-create", kwargs={"pk": representative_data["organization"].pk}), expect_errors=True
    )
    assert resp.status_code == 403


def test_representative_update_no_coordinators(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    representative_data["representative_viisp_coordinator"].role = "resource_manager"
    representative_data["representative_viisp_coordinator"].save()
    representative_data["resource_representative_coordinator"].role = "resource_manager"
    representative_data["resource_representative_coordinator"].save()
    form = app.get(
        reverse(
            "representative-update",
            kwargs={
                "pk": representative_data["organization"].pk,
                "representative_id": representative_data["open_data_representative_coordinator"].pk,
            },
        )
    ).forms["representative-form"]
    form["role"] = "open_data_manager"
    resp = form.submit()
    assert len(resp.context["form"].errors) == 1


def test_representative_update_with_correct_data(app: DjangoTestApp, representative_data):
    representative_data["open_data_representative_manager"].user = representative_data["open_data_manager"]
    representative_data["open_data_representative_manager"].save()
    app.set_user(representative_data["open_data_coordinator"])
    form = app.get(
        reverse(
            "representative-update",
            kwargs={
                "pk": representative_data["organization"].pk,
                "representative_id": representative_data["open_data_representative_manager"].pk,
            },
        )
    ).forms["representative-form"]
    form["role"] = "open_data_coordinator"
    resp = form.submit()
    representative_data["open_data_representative_manager"].refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse("organization-members", kwargs={"pk": representative_data["organization"].pk})
    assert representative_data["open_data_representative_manager"].role == "open_data_coordinator"
    assert (
        representative_data["open_data_representative_manager"].user.organization == representative_data["organization"]
    )


def test_representative_update_can_make_agreements(app: DjangoTestApp, representative_data):
    app.set_user(representative_data["viisp_coordinator"])
    form = app.get(
        reverse(
            "representative-update",
            kwargs={
                "pk": representative_data["organization"].pk,
                "representative_id": representative_data["open_data_representative_manager"].pk,
            },
        )
    ).forms["representative-form"]
    form["can_make_agreements"] = True
    resp = form.submit()
    representative_data["open_data_representative_manager"].refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse("organization-members", kwargs={"pk": representative_data["organization"].pk})
    assert representative_data["open_data_representative_manager"].can_make_agreements


def test_organization_plan_create_with_no_publisher(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    app.set_user(rep.user)

    form = app.get(reverse("organization-plans-create", args=[organization.pk])).forms["plan-form"]
    form["title"] = "Test plan"
    form["description"] = "Plan for testing"
    form["publisher"] = ""
    resp = form.submit()

    assert list(resp.context["form"].errors.values()) == [
        ["Turi būti nurodytas paslaugų teikėjas arba paslaugų teikėjo pavadinimas."]
    ]


def test_organization_plan_create_with_multiple_publishers(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    app.set_user(rep.user)

    form = app.get(reverse("organization-plans-create", args=[organization.pk])).forms["plan-form"]
    form["title"] = "Test plan"
    form["description"] = "Plan for testing"
    form["publisher"].force_value(organization.pk)
    form["provider_title"] = "Publisher"
    resp = form.submit()

    assert list(resp.context["form"].errors.values()) == [
        ["Turi būti nurodytas arba paslaugų teikėjas, arba paslaugų teikėjo pavadinimas, bet ne abu."]
    ]


def test_organization_plan_create(app: DjangoTestApp):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    rep.user.organization = organization
    rep.user.save()
    app.set_user(rep.user)

    form = app.get(reverse("organization-plans-create", args=[organization.pk])).forms["plan-form"]
    form["title"] = "Test plan"
    form["description"] = "Plan for testing"
    resp = form.submit()

    assert resp.url == reverse("organization-plans", args=[organization.pk])
    assert Plan.objects.count() == 1
    assert Plan.objects.first().title == "Test plan"
    assert Plan.objects.first().description == "Plan for testing"
    assert Plan.objects.first().receiver == organization


def test_organization_plan_update(app: DjangoTestApp):
    plan = PlanFactory()
    ct = ContentType.objects.get_for_model(plan.receiver)
    rep = RepresentativeFactory(content_type=ct, object_id=plan.receiver.pk, role=Representative.OPEN_DATA_MANAGER)
    app.set_user(rep.user)

    form = app.get(reverse("plan-change", args=[plan.receiver.pk, plan.pk])).forms["plan-form"]
    form["title"] = "Test plan (updated)"
    form["publisher"].force_value(plan.receiver.pk)
    resp = form.submit()

    assert resp.url == reverse("plan-detail", args=[plan.receiver.pk, plan.pk])
    assert Plan.objects.count() == 1
    assert Plan.objects.first().title == "Test plan (updated)"
    assert Plan.objects.first().publisher == plan.receiver


def test_organization_merge_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    organization = OrganizationFactory()
    resp = app.get(reverse("merge-organizations", args=[organization.pk]), expect_errors=True)

    assert resp.status_code == 403


def test_organization_merge(app: DjangoTestApp):
    user = UserFactory(is_superuser=True)
    app.set_user(user)

    organization = OrganizationFactory()
    organization_id = organization.pk
    merge_organization = OrganizationFactory()

    dataset = DatasetFactory(organization=organization)
    request = RequestFactory()
    request.organizations.add(organization)
    representative = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(organization), object_id=organization.pk
    )

    form = app.get(reverse("confirm-organization-merge", args=[organization.pk, merge_organization.pk])).forms[
        "confirm-merge-form"
    ]
    resp = form.submit()

    assert resp.url == reverse("organization-detail", args=[merge_organization.pk])
    assert Organization.objects.filter(pk=organization_id).count() == 0
    assert list(merge_organization.dataset_set.all()) == [dataset]
    assert list(merge_organization.request_set.all()) == [request]
    assert list(
        Representative.objects.filter(
            content_type=ContentType.objects.get_for_model(merge_organization), object_id=merge_organization.pk
        )
    ) == [representative]


def test_organization_open_plans(app: DjangoTestApp):
    organization = OrganizationFactory()
    PlanFactory(is_closed=True, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)

    resp = app.get(reverse("organization-plans", args=[organization.pk]))
    assert len(resp.context["plans"]) == 2


def test_organization_closed_plans(app: DjangoTestApp):
    organization = OrganizationFactory()
    PlanFactory(is_closed=True, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)
    PlanFactory(is_closed=False, receiver=organization)

    resp = app.get("%s?status=closed" % reverse("organization-plans", args=[organization.pk]))
    assert len(resp.context["plans"]) == 1


def test_change_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    response = app.get(reverse("organization-change", kwargs={"pk": org.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


def test_change_form_wrong_login(app: DjangoTestApp):
    org = OrganizationFactory()
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse("organization-change", kwargs={"pk": org.id}))
    assert response.status_code == 302
    assert str(org.id) in response.location


def generate_photo_file(height, length) -> bytes:
    file = io.BytesIO()
    image = Image.new("RGBA", size=(height, length), color=(155, 0, 0))
    image.save(file, "png")
    file.name = "img.png"
    return file.getvalue()


def test_change_form_correct_login(app: DjangoTestApp):
    representative = ViispRepresentativeFactory()
    org = representative.content_object
    jurisdiction = AreaOfManagementFactory(id=30, name_lt="Jurisdiction30", name_en="Jurisdiction30")

    user = representative.user
    app.set_user(user)

    form = app.get(reverse("organization-change", kwargs={"pk": org.id})).forms["organization-form"]

    form["title"] = "Edited title"
    form["description"] = "edited org description"
    form["jurisdiction"] = jurisdiction.id
    form["image"] = Upload("img.png", generate_photo_file(300, 300), "image")

    resp = form.submit()
    org.refresh_from_db()

    assert resp.status_code == 302
    assert resp.url == reverse("organization-detail", kwargs={"pk": org.id})
    assert org.title == "Edited title"
    assert org.description == "edited org description"


def test_click_edit_button(app: DjangoTestApp):
    representative = ViispRepresentativeFactory()
    org = representative.content_object
    user = representative.user
    app.set_user(user)
    response = app.get(reverse("organization-detail", kwargs={"pk": org.id}))
    response.click(linkid="change_organization")
    assert response.status_code == 200


def test_contact_tab_access_coordinator(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])

    resp = app.get(reverse("organization-contacts", kwargs={"pk": representative_data["organization"].pk}))

    assert resp.status_code == 200
    assert "Kontaktai" in resp.text
    assert "contacts/add" in resp.text


def test_contact_tab_access_denied_for_manager(app, representative_data):
    app.set_user(representative_data["open_data_manager"])

    resp = app.get(
        reverse("organization-contacts", kwargs={"pk": representative_data["organization"].pk}), expect_errors=True
    )

    assert resp.status_code == 403


def test_contact_tab_display_org_contacts(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    organization = representative_data["organization"]

    ContactFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        email="org@test.com",
        phone="+37061234567",
    )

    resp = app.get(reverse("organization-contacts", kwargs={"pk": organization.pk}))

    assert resp.status_code == 200
    assert "org@test.com" in resp.text
    assert "+37061234567" in resp.text
    assert organization.title in resp.text


def test_contact_tab_display_user_contacts(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    organization = representative_data["organization"]
    user = representative_data["open_data_manager"]

    ContactFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(user),
        object_id=user.pk,
        email="user@test.com",
        phone="+37061234567",
    )

    resp = app.get(reverse("organization-contacts", kwargs={"pk": organization.pk}))

    assert resp.status_code == 200
    assert "user@test.com" in resp.text
    assert "+37061234567" in resp.text
    assert user.get_full_name() in resp.text


def test_contact_tab_display_multiple_contacts(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    organization = representative_data["organization"]
    user1 = UserFactory(organization=organization)
    user2 = UserFactory(organization=organization)

    contacts = [
        ContactFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            email="org@test.com",
            phone="+37061234567",
        ),
        ContactFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(user1),
            object_id=user1.pk,
            email="user1@test.com",
            phone="+37067654321",
        ),
        ContactFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(user2),
            object_id=user2.pk,
            email="user2@test.com",
            phone="+37061111111",
        ),
    ]

    resp = app.get(reverse("organization-contacts", kwargs={"pk": organization.pk}))

    assert resp.status_code == 200

    for contact in contacts:
        assert contact.email in resp.text
        assert contact.phone in resp.text

    assert organization.title in resp.text
    assert user1.get_full_name() in resp.text
    assert user2.get_full_name() in resp.text


def test_contact_tab_pagination(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    organization = representative_data["organization"]

    for i in range(15):
        user = UserFactory(organization=organization)
        ContactFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
            email=f"user{i}@test.com",
        )

    resp = app.get(reverse("organization-contacts", kwargs={"pk": organization.pk}))

    assert resp.status_code == 200
    assert "page=2" in resp.text

    soup = BeautifulSoup(resp.content, "html.parser")
    rows = soup.find("table").find("tbody").find_all("tr")
    assert len(rows) == 10


def test_contact_tab_empty_state(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])

    resp = app.get(reverse("organization-contacts", kwargs={"pk": representative_data["organization"].pk}))

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    rows = soup.find("table")
    assert rows is None


def test_contact_tab_actions_coordinator(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    organization = representative_data["organization"]

    contact = ContactFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        email="test@test.com",
    )

    resp = app.get(reverse("organization-contacts", kwargs={"pk": organization.pk}))

    assert resp.status_code == 200
    assert f"contacts/{contact.pk}/change" in resp.text
    assert f"contacts/{contact.pk}/delete" in resp.text


def test_contact_create_for_org(app, representative_data):
    org = representative_data["organization"]
    app.set_user(representative_data["open_data_coordinator"])
    form = app.get(reverse("contact-create", kwargs={"pk": org.pk})).forms["contact-form"]

    form["contact"] = f"org-{org.pk}"
    form["email"] = "org@test.com"
    form["phone"] = "+37061234567"

    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse("organization-contacts", kwargs={"pk": org.pk})

    contact = Contact.objects.first()
    assert contact.content_type == ContentType.objects.get_for_model(org)
    assert contact.object_id == org.pk
    assert contact.email == "org@test.com"
    assert contact.phone == "+37061234567"
    assert contact.organization == org
    assert contact.kind == Contact.Kind.ORG

    resp = app.get(reverse("organization-contacts", kwargs={"pk": org.pk}))
    assert resp.status_code == 200
    assert contact.email in resp.text
    assert contact.phone in resp.text
    assert org.title in resp.text


def test_contact_create_for_user_valid_data(app, representative_data):
    org = representative_data["organization"]
    app.set_user(representative_data["open_data_coordinator"])
    coordinator = representative_data["open_data_coordinator"]
    form = app.get(reverse("contact-create", kwargs={"pk": org.pk})).forms["contact-form"]
    form["contact"] = f"user-{coordinator.pk}"
    form["email"] = "user@test.com"
    form["phone"] = "+37061234567"
    form["position"] = "Tester"

    resp = form.submit()
    assert resp.status_code == 302

    contact = Contact.objects.first()
    assert contact.content_type == ContentType.objects.get_for_model(coordinator)
    assert contact.object_id == coordinator.pk
    assert contact.email == "user@test.com"
    assert contact.phone == "+37061234567"
    assert contact.kind == Contact.Kind.INDIVIDUAL

    resp = app.get(reverse("organization-contacts", kwargs={"pk": org.pk}))
    assert resp.status_code == 200
    assert contact.email in resp.text
    assert contact.phone in resp.text
    assert coordinator.get_full_name() in resp.text


def test_contact_create_for_non_registered_contact(app, representative_data):
    org = representative_data["organization"]
    app.set_user(representative_data["open_data_coordinator"])

    form = app.get(reverse("contact-create", kwargs={"pk": org.pk})).forms["contact-form"]

    form["contact_name"] = "Test Testeron"
    form["email"] = "user@test.com"
    form["phone"] = "+37061234567"
    form["position"] = "Tester"

    resp = form.submit()
    assert resp.status_code == 302

    contact = Contact.objects.first()
    assert contact.content_type is None
    assert contact.object_id is None
    assert contact.organization == org
    assert contact.contact_name == "Test Testeron"
    assert contact.position == "Tester"
    assert contact.email == "user@test.com"
    assert contact.phone == "+37061234567"
    assert contact.kind == Contact.Kind.UNREGISTERED

    resp = app.get(reverse("organization-contacts", kwargs={"pk": org.pk}))
    assert resp.status_code == 200
    assert contact.contact_name in resp.text
    assert contact.position in resp.text
    assert contact.email in resp.text
    assert contact.phone in resp.text


def test_contact_create_no_permission(app, representative_data):
    app.set_user(representative_data["open_data_manager"])
    resp = app.get(reverse("contact-create", kwargs={"pk": representative_data["organization"].pk}), expect_errors=True)
    assert resp.status_code == 403


def test_contact_update_org(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    org = representative_data["organization"]
    contact = ContactFactory(
        organization=org,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        email="old@test.com",
        phone="+37061234567",
    )

    form = app.get(reverse("contact-update", kwargs={"pk": org.pk, "contact_id": contact.pk})).forms["contact-form"]

    form["email"] = "updated@test.com"
    form["phone"] = "+37067654321"

    resp = form.submit()
    assert resp.status_code == 302

    contact.refresh_from_db()
    assert contact.email == "updated@test.com"
    assert contact.phone == "+37067654321"
    assert contact.kind == Contact.Kind.ORG


def test_contact_update_user(app, representative_data):
    coordinator = representative_data["open_data_coordinator"]
    app.set_user(coordinator)
    org = representative_data["organization"]
    contact = ContactFactory(
        organization=org,
        content_type=ContentType.objects.get_for_model(coordinator),
        object_id=coordinator.pk,
        email="old@test.com",
        phone="+37061234567",
        position="Tester",
    )
    form = app.get(reverse("contact-update", kwargs={"pk": org.pk, "contact_id": contact.pk})).forms["contact-form"]

    form["email"] = "updated@test.com"

    resp = form.submit()
    assert resp.status_code == 302

    contact.refresh_from_db()
    assert contact.email == "updated@test.com"
    assert contact.kind == Contact.Kind.INDIVIDUAL


def test_contact_delete(app, representative_data):
    app.set_user(representative_data["open_data_coordinator"])
    org = representative_data["organization"]
    contact = ContactFactory(
        organization=org,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
    )
    url = reverse("organization-contacts", kwargs={"pk": org.pk})
    resp = app.get(url)
    resp = resp.click(linkid=f"delete-contact-{contact.pk}-btn")
    form = resp.forms["delete-form"]
    resp = form.submit()

    assert resp.headers["location"] == url
    assert resp.status_code == 302
    c = Contact.objects.filter(pk=contact.pk)
    assert not c.exists()


def test_contact_delete_no_permission(app, representative_data):
    app.set_user(representative_data["open_data_manager"])  # Manager shouldn't have permission
    org = representative_data["organization"]
    contact = ContactFactory(
        organization=org,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
    )

    resp = app.get(reverse("contact-delete", kwargs={"pk": org.pk, "contact_id": contact.pk}), expect_errors=True)

    assert resp.status_code == 403
    assert Contact.objects.count() == 1


@pytest.mark.django_db
def test_contact_delete_blocked_if_assigned_to_agreements(app, representative_data):
    # Arrange
    user = representative_data["open_data_coordinator"]
    organization = representative_data["organization"]
    app.set_user(user)

    contact = ContactFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
    )
    AgreementFactory(
        assigner=organization,
        assignee=organization,
        assigner_representative=contact,
        status=AgreementStatuses.CREATED,
        created_by=user,
    )

    url = reverse("contact-delete", kwargs={"pk": organization.pk, "contact_id": contact.pk})

    # Act
    response = app.get(url, expect_errors=True)

    # Assert
    assert response.status_code == 302
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_non_gov_organizaton_no_gov_kind(app: DjangoTestApp):
    representative = ViispRepresentativeFactory()
    org = representative.content_object

    user = representative.user
    app.set_user(user)

    form = app.get(reverse("organization-change", kwargs={"pk": org.id})).forms["organization-form"]

    kind_values = [value for value, _, _ in form["kind"].options]

    assert len(kind_values) == 2
    assert Organization.GOV not in kind_values


def test_gov_organizaton_cannot_select_different_kind(app: DjangoTestApp):
    representative = ViispRepresentativeFactory()
    org = representative.content_object
    org.kind = Organization.GOV
    org.save()

    user = representative.user
    app.set_user(user)

    form = app.get(reverse("organization-change", kwargs={"pk": org.id})).forms["organization-form"]

    kind_values = [value for value, _, _ in form["kind"].options]

    assert len(kind_values) == 1
    assert kind_values[0] == Organization.GOV


def test_create_organization(app: DjangoTestApp):
    user = UserFactory(is_superuser=True)
    app.set_user(user)

    form = app.get(reverse("organization-create")).forms["organization-form"]

    form["company_code"] = "123456789"
    form["title"] = "Imone"
    form["name"] = "kodinis_pavadinimas"
    jurisdiction = AreaOfManagement.objects.first()
    form["jurisdiction"] = jurisdiction.pk
    form["email"] = "example@example.com"
    form["phone"] = "061234567"
    form["address"] = "Gatve 1"
    form["description"] = "aprasymas"
    form["kind"] = Organization.GOV

    response = form.submit()

    assert response.status_code == 302

    organization = Organization.objects.get(company_code="123456789")
    assert organization.title == "Imone"
    assert organization.name == "datasets/gov/kodinis-pavadinimas/"
    assert organization.jurisdiction == jurisdiction
    assert organization.email == "example@example.com"
    assert organization.phone == "061234567"
    assert organization.address == "Gatve 1"
    assert organization.description == "aprasymas"
    assert organization.kind == Organization.GOV


def test_partner_register_no_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    response = app.get(reverse("partner-register"))

    assert response.status_code == 302
    assert response.url == reverse("viisp-login")


def test_partner_register_access_with_permission(app: DjangoTestApp):
    user = UserFactory(is_viisp_login=True)
    app.set_user(user)

    response = app.get(reverse("partner-register"))

    assert response.status_code == 200


class TestRepresentativeDeleteView:
    def test_delete_representative(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)

        organization = OrganizationFactory()
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization.pk,
        )

        app.post(reverse("representative-delete", args=[organization.pk, representative.pk]))

        assert not Representative.objects.filter(pk=representative.pk).exists()

    def test_remove_publisher_from_all_representative_organization_datasets(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)

        organization = OrganizationFactory()
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization.pk,
            organization=organization,
        )
        dataset = DatasetFactory(organization=organization, publisher=organization)

        app.post(reverse("representative-delete", args=[organization.pk, representative.pk]))

        dataset.refresh_from_db()
        assert dataset.publisher is None


class TestOrganizationApiKeysDeleteView:
    def test_delete_api_client_if_spinta_request_successful(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)
        organization = OrganizationFactory()
        api_key = APIKeyFactory()

        with patch(
            "vitrina.orgs.views.OrganizationApiKeysDeleteView.spinta_delete_apikey",
            return_value=Mock(status_code=204),
        ) as api_delete_request_mock:
            app.post(
                reverse("organization-apikeys-delete", args=[organization.pk, api_key.pk]),
            )

            assert not ApiKey.objects.exists()
            api_delete_request_mock.assert_called_once()

    def test_do_not_delete_api_client_if_spinta_request_unsuccessful(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)
        organization = OrganizationFactory()
        api_key = APIKeyFactory()

        with patch(
            "vitrina.orgs.views.OrganizationApiKeysDeleteView.spinta_delete_apikey",
            return_value=Mock(status_code=500),
        ) as api_delete_request_mock:
            app.post(
                reverse("organization-apikeys-delete", args=[organization.pk, api_key.pk]),
            )

            assert ApiKey.objects.exists()
            api_delete_request_mock.assert_called_once()


class TestOrganizationBasedAgreementList:
    def test_success(self, app: DjangoTestApp, organization: Organization):
        # Arrange
        status_priority = {
            AgreementStatuses.SUBMITTED: 0,
            AgreementStatuses.APPROVED: 1,
            AgreementStatuses.INITIATED: 2,
            AgreementStatuses.ACTIVE: 3,
            AgreementStatuses.SIGNED: 4,
            AgreementStatuses.CREATED: 5,
            AgreementStatuses.FORMED: 6,
            AgreementStatuses.TERMINATED: 7,
        }

        representative = RepresentativeFactory(content_object=organization)
        user = representative.user
        app.set_user(user)

        now = datetime.now(tz=timezone)

        agreements = [
            AgreementFactory(assigner=organization, status=status, created_at=now) for status in AgreementStatuses
        ]
        older_agreement = AgreementFactory(
            assigner=organization,
            status=AgreementStatuses.CREATED,
            created_at=now - timedelta(days=1),
        )
        newer_agreement = AgreementFactory(
            assigner=organization,
            status=AgreementStatuses.CREATED,
            created_at=now,
        )
        agreements.extend([older_agreement, newer_agreement])

        expected_agreement_order = sorted(
            agreements,
            key=lambda agreement: (status_priority.get(agreement.status, 8), agreement.created_at),
        )
        ordered_expected_agreement_ids = [agreement.uuid for agreement in expected_agreement_order]

        # Act
        response = app.get(reverse("organization-agreement-list", args=[organization.pk]))

        # Assert
        assert response.status_code == 200
        response_agreement_ids = [item.uuid for item in response.context["agreements"]]
        assert response_agreement_ids == ordered_expected_agreement_ids

    def test_list_agreements_as_superuser(self, app: DjangoTestApp, organization: Organization):
        user = UserFactory(is_superuser=True)
        app.set_user(user)

        AgreementFactory.create_batch(3, assigner=organization)

        url = reverse("organization-agreement-list", args=[organization.pk])
        response = app.get(url)

        assert response.status_code == 200
        assert response.context["agreements"].count() == 3

    def test_cannot_list_unauthenticated(self, app: DjangoTestApp, organization: Organization):
        # AnonymousUser is used, since no user is set.
        url = reverse("organization-agreement-list", args=[organization.pk])
        response = app.get(url, expect_errors=True)
        assert response.status_code == 302  # login redirect

    def test_cannot_list_if_not_representative(self, app: DjangoTestApp, organization: Organization):
        user = UserFactory()
        app.set_user(user)

        url = reverse("organization-agreement-list", args=[organization.pk])
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403

    def test_cannot_list_if_representative_of_another_organization(
        self, app: DjangoTestApp, organization: Organization
    ):
        other_organization = OrganizationFactory()

        representative = RepresentativeFactory(content_object=other_organization)
        user = representative.user

        AgreementFactory(assigner=organization)
        app.set_user(user)

        url = reverse("organization-agreement-list", args=[organization.pk])
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403


class TestOrganizationBasedAgreementDetail:
    def test_success(self, app, organization: Organization):
        representative = RepresentativeFactory(content_object=organization)
        user = representative.user
        app.set_user(user)

        agreement = AgreementFactory(assigner=organization)

        url = reverse(
            "organization-agreement-detail",
            args=[organization.pk, agreement.uuid],
        )
        response = app.get(url)
        assert response.status_code == 200

        context_agreement = response.context["agreement"]
        assert context_agreement == agreement

        assert response.context["can_create_agreements"] is False
        assert response.context["can_submit_agreements"] is False
        assert "can_approve_agreements" in response.context
        assert "can_form_agreements" in response.context
        assert "can_sign_agreements" in response.context
        assert "can_upload_agreement_file" in response.context

    def test_permission_denied_for_unrelated_user(self, app, organization: Organization):
        unrelated_user = UserFactory()
        app.set_user(unrelated_user)

        agreement = AgreementFactory(assigner=organization)

        url = reverse(
            "organization-agreement-detail",
            args=[organization.pk, agreement.uuid],
        )
        response = app.get(url, expect_errors=True)
        assert response.status_code == 403  # Permission denied

    def test_not_found_for_wrong_organization(self, app, organization: Organization):
        representative = RepresentativeFactory(content_object=organization)
        app.set_user(representative.user)

        other_organization = OrganizationFactory(title="Other Org")
        agreement = AgreementFactory(assigner=other_organization)

        url = reverse(
            "organization-agreement-detail",
            args=[organization.pk, agreement.uuid],
        )
        response = app.get(url, expect_errors=True)
        assert response.status_code == 404


class TestOrganizationBasedAgreementNegotiateApprove:
    def test_success(self, app: DjangoTestApp, dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(settings.BASE_DIR / "tests/smart_contracts/files/contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )

        app.set_user(assigner_user)

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)
        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)

        project = ProjectFactory(
            organization=assignee_organization, datasets=[dataset], other_assignee_legislations="Test"
        )

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(assignee_user),
            email=assignee_user.email,
            phone=assignee_user.phone,
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(assigner_user),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=None,
            created_by=assignee_user,
            status=AgreementStatuses.SUBMITTED,
        )

        # Act
        response = app.post(
            reverse("organization-agreement-approve", args=[assigner_organization.pk, agreement.pk]),
            {
                "template": template.pk,
                "assigner_representative": assigner_contact.pk,
                "other_assigner_legislations": "Legislation A; Legislation B",
            },
        )

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.APPROVED
        assert agreement.template == template
        assert agreement.assigner_representative == assigner_contact
        assert agreement.other_assigner_legislations == "Legislation A; Legislation B"

    def test_unauthorized_not_representative(self, app: DjangoTestApp, dataset):
        # Arrange
        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        unauthorized_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(unauthorized_user)

        project = ProjectFactory(organization=assignee_organization, datasets=[dataset])
        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assigner=assigner_organization,
            assigner_representative=None,
            status=AgreementStatuses.SUBMITTED,
        )

        template_file = ContentFile(b"test", name="template.md")

        # Act
        response = app.post(
            reverse("organization-agreement-approve", args=[assigner_organization.pk, agreement.pk]),
            {
                "template": template_file,
                "assigner_representative": None,
                "other_assigner_legislations": "",
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.SUBMITTED
        assert not agreement.template
        assert not agreement.assigner_representative
        assert not agreement.other_assigner_legislations

    def test_unauthorized_no_approval_rights(self, app: DjangoTestApp, dataset):
        # Arrange
        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=False)

        project = ProjectFactory(organization=assignee_organization, datasets=[dataset])
        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assigner=assigner_organization,
            status=AgreementStatuses.SUBMITTED,
        )

        template_file = ContentFile(b"test", name="template.md")

        # Act
        response = app.post(
            reverse("organization-agreement-approve", args=[assigner_organization.pk, agreement.pk]),
            {
                "template": template_file,
                "assigner_representative": None,
                "other_assigner_legislations": "",
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.SUBMITTED

    @pytest.mark.parametrize(
        "status",
        [
            AgreementStatuses.CREATED,
            AgreementStatuses.APPROVED,
            AgreementStatuses.FORMED,
            AgreementStatuses.INITIATED,
            AgreementStatuses.SIGNED,
            AgreementStatuses.ACTIVE,
            AgreementStatuses.TERMINATED,
        ],
    )
    def test_incorrect_agreement_status(self, app: DjangoTestApp, dataset, status):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(settings.BASE_DIR / "tests/smart_contracts/files/contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )

        app.set_user(assigner_user)

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)
        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)

        project = ProjectFactory(
            organization=assignee_organization, datasets=[dataset], other_assignee_legislations="Test"
        )

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(assignee_user),
            email=assignee_user.email,
            phone=assignee_user.phone,
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(assigner_user),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=None,
            created_by=assignee_user,
            status=status,
        )

        # Act
        response = app.post(
            reverse("organization-agreement-approve", args=[assigner_organization.pk, agreement.pk]),
            {
                "template": template.pk,
                "assigner_representative": assigner_contact.pk,
                "other_assigner_legislations": "",
            },
        )

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == status
        assert not agreement.template
        assert not agreement.assigner_representative
        assert not agreement.other_assigner_legislations


class TestOrganizationBasedAgreementNegotiateForm:
    def test_success(self, app, dataset: Dataset):
        """Test successful organization-based agreement form submission by the assigner."""
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(settings.BASE_DIR / "tests/smart_contracts/files/contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assigner_organization
        dataset.save()

        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone,
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assignee_user,
            status=AgreementStatuses.APPROVED,
        )

        # Act
        response = app.post(reverse("organization-agreement-form", args=[assigner_organization.pk, agreement.pk]), {})

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.FORMED

        odrl_file, contract, template_copy = list(agreement.files.order_by("is_template", "created_at"))

        assert odrl_file.file_name.endswith(".json")
        odrl_content = json.loads(odrl_file.file.read())
        assert odrl_content == {
            "@context": {
                "@vocab": "http://www.w3.org/ns/odrl.jsonld",
                "ex": "http://example.org/vocab#",
            },
            "uid": f"https://data.gov.lt/ID/datasets/gov/vssa/ror/dcat/Agreement/{agreement.pk}",
            "type": "Agreement",
            "profile": "http://www.w3.org/ns/odrl/profile/core",
            "issued": odrl_content["issued"],
            "assigner": [
                {
                    "uid": str(assigner_organization.pk),
                    "ex:companyName": assigner_organization.title,
                    "ex:companyCode": assigner_organization.company_code,
                    "ex:address": assigner_organization.address,
                    "ex:representative": agreement.assigner_representative_full_name,
                    "ex:email": assigner_organization.email,
                    "ex:phone": assigner_organization.phone,
                    "ex:personalCode": " - ",
                }
            ],
            "assignee": [
                {
                    "uid": str(assignee_organization.pk),
                    "ex:companyName": assignee_organization.title,
                    "ex:companyCode": assignee_organization.company_code,
                    "ex:address": assignee_organization.address,
                    "ex:representative": agreement.assignee_representative_full_name,
                    "ex:email": assignee_organization.email,
                    "ex:phone": assignee_organization.phone,
                    "ex:personalCode": " - ",
                }
            ],
            "permission": [
                {
                    "target": {
                        "uid": dataset.pk,
                        "ex:name": dataset.title,
                        "ex:scopes": [],
                    }
                }
            ],
            "ex:paymentTerms": agreement.payment_terms,
            "ex:otherAssignerLegislations": agreement.other_assigner_legislations,
            "ex:otherAssigneeLegislations": project.other_assignee_legislations,
        }

        assert not contract.is_template
        assert contract.checksum
        contract.file.seek(0)
        contract_content = extract_text(io.BytesIO(contract.file.read()))
        expected_contract_values = [
            odrl_content["issued"],
            odrl_content["assigner"][0]["ex:companyName"],
            odrl_content["assigner"][0]["ex:companyCode"],
            odrl_content["assigner"][0]["ex:address"].split("\n")[0],
            odrl_content["assigner"][0]["ex:email"],
            odrl_content["assigner"][0]["ex:phone"],
            odrl_content["assigner"][0]["ex:representative"],
            odrl_content["assigner"][0]["ex:personalCode"],
            odrl_content["assignee"][0]["ex:companyName"],
            odrl_content["assignee"][0]["ex:companyCode"],
            odrl_content["assignee"][0]["ex:address"].split("\n")[0],
            odrl_content["assignee"][0]["ex:email"],
            odrl_content["assignee"][0]["ex:phone"],
            odrl_content["assignee"][0]["ex:representative"],
            odrl_content["assignee"][0]["ex:personalCode"],
            odrl_content["permission"][0]["target"]["ex:name"],
            *odrl_content["permission"][0]["target"].get("ex:scopes", []),
            odrl_content["ex:paymentTerms"],
            odrl_content["ex:otherAssignerLegislations"],
            odrl_content["ex:otherAssigneeLegislations"],
        ]
        # Ensure all required values from odrl were transferred to the contract.
        for index, value in enumerate(expected_contract_values):
            if value := str(value).strip():
                assert value in contract_content, f"Expected '{value}' (index={index}) not found in PDF."

        assert template_copy.is_template
        assert template_copy.file.path != template.file.path
        assert template_copy.file.read() == template.file.read()
        assert template_copy.checksum

    def test_unauthorized_not_representative(self, app, dataset: Dataset):
        """Assigner without representative rights cannot form agreement."""
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(settings.BASE_DIR / "tests/smart_contracts/files/contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assignee_organization
        dataset.save()

        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        # No signing rights
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=False)

        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone,
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assigner_user,
            status=AgreementStatuses.APPROVED,
        )

        response = app.post(
            reverse("organization-agreement-form", args=[assigner_organization.pk, agreement.pk]),
            {},
            expect_errors=True,
        )

        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.APPROVED
        assert not agreement.files.exists()

    def test_unauthorized_not_viisp_authorized(self, app, dataset: Dataset):
        """Assigner not VIISP-authorized cannot form an agreement."""
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(settings.BASE_DIR / "tests/smart_contracts/files/contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assignee_organization
        dataset.save()

        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=False,
            viisp_company_code="invalid",
        )
        app.set_user(assigner_user)

        # Has signing rights but invalid Viisp
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone,
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assigner_user,
            status=AgreementStatuses.APPROVED,
        )

        response = app.post(
            reverse("organization-agreement-form", args=[assigner_organization.pk, agreement.pk]),
            {},
            expect_errors=True,
        )

        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.APPROVED
        assert not agreement.files.exists()

    @pytest.mark.parametrize(
        "initial_status",
        [
            AgreementStatuses.CREATED,
            AgreementStatuses.SUBMITTED,
            AgreementStatuses.FORMED,
            AgreementStatuses.INITIATED,
            AgreementStatuses.SIGNED,
            AgreementStatuses.ACTIVE,
            AgreementStatuses.TERMINATED,
        ],
    )
    def test_incorrect_agreement_status(self, initial_status, app, dataset: Dataset):
        """Cannot form an agreement if status is not APPROVED."""
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(settings.BASE_DIR / "tests/smart_contracts/files/contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assignee_organization
        dataset.save()

        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assignee_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assigner_user,
            status=initial_status,
        )

        response = app.post(
            reverse("organization-agreement-form", args=[assigner_organization.pk, agreement.pk]),
            {},
            expect_errors=True,
        )

        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == initial_status
        assert not agreement.files.exists()


class TestOrganizationBasedAgreementNegotiateSign:
    def test_success(self, app: DjangoTestApp, agreement_pdf: Path, agreement_two_signers: str, odrl_json: Path):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile("### Template content", name="contract_template.md")
        )

        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.email,
        )
        ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.email,
        )

        project = ProjectFactory(organization=assignee_organization)
        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            status=AgreementStatuses.INITIATED,
            created_by=assignee_user,
        )

        AgreementJSONFileFactory(agreement=agreement, json_path=odrl_json)
        AgreementPDFFileFactory(agreement=agreement, pdf_path=agreement_pdf)
        app.set_user(assigner_user)

        # Act
        response = app.post(
            reverse("organization-agreement-sign", args=[assigner_organization.pk, agreement.pk]),
            upload_files=[("file", "agreement.adoc", agreement_two_signers.read_bytes(), "text/plain")],
        )

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.SIGNED
        assert agreement.is_agent_sync_enabled

    @pytest.mark.parametrize(
        "initial_status",
        [
            AgreementStatuses.CREATED,
            AgreementStatuses.SUBMITTED,
            AgreementStatuses.APPROVED,
            AgreementStatuses.SIGNED,
            AgreementStatuses.ACTIVE,
            AgreementStatuses.TERMINATED,
        ],
    )
    def test_incorrect_status(
        self, initial_status, app: DjangoTestApp, agreement_pdf: Path, agreement_two_signers: str, odrl_json: Path
    ):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile("### Template content", name="contract_template.md")
        )

        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.email,
        )
        ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.email,
        )

        project = ProjectFactory(organization=assignee_organization)
        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            status=initial_status,
            created_by=assignee_user,
        )

        AgreementJSONFileFactory(agreement=agreement, json_path=odrl_json)
        AgreementPDFFileFactory(agreement=agreement, pdf_path=agreement_pdf)
        app.set_user(assigner_user)

        # Act
        response = app.post(
            reverse("organization-agreement-sign", args=[assigner_organization.pk, agreement.pk]),
            upload_files=[("file", "agreement.adoc", agreement_two_signers.read_bytes(), "text/plain")],
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 200
        assert "form" in response.context
        assert "Pasirašyti galima tik sutartis su būsenomis" in str(response.context["form"].errors.get("file", ""))
        agreement.refresh_from_db()
        assert agreement.status == initial_status

    def test_pdf_file_missing(self, app: DjangoTestApp, agreement_two_signers: str):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile("### Template content", name="contract_template.md")
        )

        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        assigner_user = UserFactory(
            organization=assigner_organization,
            viisp_company_code=assigner_organization.company_code,
            is_viisp_login=True,
        )
        assignee_user = UserFactory(organization=assignee_organization)

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
        )

        project = ProjectFactory(organization=assignee_organization)
        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            status=AgreementStatuses.INITIATED,
            created_by=assignee_user,
        )

        app.set_user(assigner_user)

        # Act
        response = app.post(
            reverse("organization-agreement-sign", args=[assigner_organization.pk, agreement.pk]),
            upload_files=[("file", "agreement.adoc", agreement_two_signers.read_bytes(), "text/plain")],
        )

        # Assert
        assert response.status_code == 302
        # Expect an error message about missing PDF
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.INITIATED

    def test_multiple_pdf_files(self, app: DjangoTestApp, agreement_pdf: Path, agreement_two_signers: str):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile("### Template content", name="contract_template.md")
        )

        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        assigner_user = UserFactory(
            organization=assigner_organization,
            viisp_company_code=assigner_organization.company_code,
            is_viisp_login=True,
        )
        assignee_user = UserFactory(organization=assignee_organization)

        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
        )

        project = ProjectFactory(organization=assignee_organization)
        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            status=AgreementStatuses.INITIATED,
            created_by=assignee_user,
        )

        # Two PDFs
        AgreementPDFFileFactory(agreement=agreement, pdf_path=agreement_pdf)
        AgreementPDFFileFactory(agreement=agreement, pdf_path=agreement_pdf)
        app.set_user(assigner_user)

        # Act
        response = app.post(
            reverse("organization-agreement-sign", args=[assigner_organization.pk, agreement.pk]),
            upload_files=[("file", "agreement.adoc", agreement_two_signers.read_bytes(), "text/plain")],
        )

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.INITIATED

    def test_wrong_signer(self, app: DjangoTestApp, agreement_pdf: Path, agreement_two_signers: str, odrl_json: Path):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile("### Template content", name="contract_template.md")
        )

        assigner_organization, assignee_organization = OrganizationFactory.create_batch(2)
        wrong_user = UserFactory(organization=assignee_organization)  # Not assigner
        assignee_user = UserFactory(organization=assignee_organization)

        RepresentativeFactory(user=wrong_user, content_object=assigner_organization, can_make_agreements=True)
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=wrong_user.pk,
            content_type=ContentType.objects.get_for_model(User),
        )

        project = ProjectFactory(organization=assignee_organization)
        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            status=AgreementStatuses.INITIATED,
            created_by=assignee_user,
        )

        AgreementJSONFileFactory(agreement=agreement, json_path=odrl_json)
        AgreementPDFFileFactory(agreement=agreement, pdf_path=agreement_pdf)
        app.set_user(wrong_user)

        # Act
        response = app.post(
            reverse("organization-agreement-sign", args=[assigner_organization.pk, agreement.pk]),
            upload_files=[("file", "agreement.adoc", agreement_two_signers.read_bytes(), "text/plain")],
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        # Status should not change because the wrong user tried to sign
        assert agreement.status == AgreementStatuses.INITIATED
