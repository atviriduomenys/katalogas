import pytest
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import ConceptFactory
from vitrina.classifiers.models import ConceptSchema, LANGUAGE_CONCEPT_SCHEMA_URI
from vitrina.datasets.factories import ContactFactory
from vitrina.datasets import ContactKind
from vitrina.datasets.models import Contact
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestDcatContactCreateView:
    def test_unauthenticated_redirects_to_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        url = reverse("dcat-contact-create", kwargs={"organization_id": org.pk})

        response = app.get(url)

        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_no_permission_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(UserFactory())

        response = app.get(
            reverse("dcat-contact-create", kwargs={"organization_id": org.pk}),
            expect_errors=True,
        )

        assert response.status_code == 403

    def test_nonexistent_organization_returns_404(self, app: DjangoTestApp):
        app.set_user(UserFactory(is_staff=True))

        response = app.get(
            reverse("dcat-contact-create", kwargs={"organization_id": 999999}),
            expect_errors=True,
        )

        assert response.status_code == 404

    @pytest.mark.parametrize("role", [Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER])
    def test_authorized_role_gets_200(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        rep = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.pk,
            role=role,
        )
        app.set_user(rep.user)

        response = app.get(reverse("dcat-contact-create", kwargs={"organization_id": org.pk}))

        assert response.status_code == 200

    @pytest.mark.parametrize("role", [Representative.OPEN_DATA_COORDINATOR, Representative.OPEN_DATA_MANAGER])
    def test_unauthorized_role_returns_403(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        rep = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.pk,
            role=role,
        )
        app.set_user(rep.user)

        response = app.get(
            reverse("dcat-contact-create", kwargs={"organization_id": org.pk}),
            expect_errors=True,
        )

        assert response.status_code == 403

    def test_valid_post_creates_contact(self, app: DjangoTestApp):
        org = OrganizationFactory()
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        app.set_user(UserFactory(is_staff=True))

        form = app.get(reverse("dcat-contact-create", kwargs={"organization_id": org.pk})).forms["contact-form"]
        form["contact_name"] = "Palaikymo paslauga"
        form["phone"] = "+37061234567"
        form["email"] = "test@example.com"
        form["served_area"] = "Vilnius"
        form["contact_options"] = "Nemokamas numeris"
        form["contact_type"] = "Pardavimų kontaktas"
        form["work_hours"] = "I-V 9:00-17:00"
        form["languages"].force_value([str(language.pk)])
        form.submit()

        contact = Contact.objects.first()
        assert contact is not None
        assert contact.contact_name == "Palaikymo paslauga"
        assert contact.phone == "+37061234567"
        assert contact.email == "test@example.com"
        assert contact.served_area == "Vilnius"
        assert contact.contact_options == "Nemokamas numeris"
        assert contact.contact_type == "Pardavimų kontaktas"
        assert contact.work_hours == "I-V 9:00-17:00"
        assert language in contact.languages.all()
        assert contact.organization == org
        assert contact.kind == ContactKind.SERVICE
        assert contact.content_type is None
        assert contact.object_id is None

    def test_valid_post_redirects_to_contacts(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(UserFactory(is_staff=True))

        form = app.get(reverse("dcat-contact-create", kwargs={"organization_id": org.pk})).forms["contact-form"]
        form["contact_name"] = "Palaikymo paslauga"
        form["phone"] = "+37061234567"
        response = form.submit()

        assert response.status_code == 302
        assert response.location == reverse("organization-contacts", kwargs={"pk": org.pk})


class TestDcatContactUpdateView:
    def test_unauthenticated_redirects_to_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind=ContactKind.SERVICE)
        url = reverse("dcat-contact-update", kwargs={"organization_id": org.pk, "contact_id": contact.pk})

        response = app.get(url)

        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_no_permission_returns_403(self, app: DjangoTestApp):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind=ContactKind.SERVICE)
        app.set_user(UserFactory())

        response = app.get(
            reverse("dcat-contact-update", kwargs={"organization_id": org.pk, "contact_id": contact.pk}),
            expect_errors=True,
        )

        assert response.status_code == 403

    def test_nonexistent_contact_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(UserFactory(is_staff=True))

        response = app.get(
            reverse("dcat-contact-update", kwargs={"organization_id": org.pk, "contact_id": 999999}),
            expect_errors=True,
        )

        assert response.status_code == 404

    def test_non_service_contact_returns_404(self, app: DjangoTestApp):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind=ContactKind.UNREGISTERED)
        app.set_user(UserFactory(is_staff=True))

        response = app.get(
            reverse("dcat-contact-update", kwargs={"organization_id": org.pk, "contact_id": contact.pk}),
            expect_errors=True,
        )

        assert response.status_code == 404

    @pytest.mark.parametrize("role", [Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER])
    def test_authorized_role_gets_200(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind=ContactKind.SERVICE)
        rep = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.pk,
            role=role,
        )
        app.set_user(rep.user)

        response = app.get(reverse("dcat-contact-update", kwargs={"organization_id": org.pk, "contact_id": contact.pk}))

        assert response.status_code == 200

    def test_valid_post_updates_contact(self, app: DjangoTestApp):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind=ContactKind.SERVICE, phone="+37061234567")
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language = ConceptFactory(concept_schemas=[language_schema])
        app.set_user(UserFactory(is_staff=True))

        form = app.get(
            reverse("dcat-contact-update", kwargs={"organization_id": org.pk, "contact_id": contact.pk})
        ).forms["contact-form"]
        form["contact_name"] = "New name"
        form["phone"] = "+37051234567"
        form["email"] = "updated@example.com"
        form["served_area"] = "Kaunas"
        form["contact_options"] = "Pagalba neprigirdintiems"
        form["contact_type"] = "PR kontaktas"
        form["work_hours"] = "II-VI 10:00-18:00"
        form["languages"].force_value([str(language.pk)])
        form.submit()

        contact.refresh_from_db()
        assert contact.contact_name == "New name"
        assert contact.phone == "+37051234567"
        assert contact.email == "updated@example.com"
        assert contact.served_area == "Kaunas"
        assert contact.contact_options == "Pagalba neprigirdintiems"
        assert contact.contact_type == "PR kontaktas"
        assert contact.work_hours == "II-VI 10:00-18:00"
        assert language in contact.languages.all()
        assert contact.kind == ContactKind.SERVICE

    def test_valid_post_redirects_to_contacts(self, app: DjangoTestApp):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind=ContactKind.SERVICE, phone="+37061234567")
        app.set_user(UserFactory(is_staff=True))

        form = app.get(
            reverse("dcat-contact-update", kwargs={"organization_id": org.pk, "contact_id": contact.pk})
        ).forms["contact-form"]
        form["contact_name"] = "Updated name"
        response = form.submit()

        assert response.status_code == 302
        assert response.location == reverse("organization-contacts", kwargs={"pk": org.pk})
