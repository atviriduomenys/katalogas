from pathlib import Path

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from tests.smart_contracts.conftest import AGREEMENT_ONE_SIGNER
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.forms import (
    OrganizationUpdateForm,
    OrganizationCreateForm,
    PartnerRegisterForm,
    RepresentativeUpdateForm,
    RepresentativeCreateForm,
)
from django_webtest import DjangoTestApp

from vitrina.orgs.models import Organization, Representative
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


class TestOrganizationUpdateForm:
    def test_organization_update_form_disables_name_for_existing_instance(self, app: DjangoTestApp):
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True, is_viisp_login=True, viisp_company_code=organization.company_code)
        app.set_user(user)
        res = app.get(reverse("organization-change", kwargs={"pk": organization.pk}))
        form = res.context["form"]

        assert isinstance(form, OrganizationUpdateForm)
        assert form.fields["name"].disabled is True
        assert "disabled" in form.fields["name"].widget.attrs


class TestOrganizationBaseForm:
    def test_phone_invalid_fails_validation(self, app: DjangoTestApp):
        user = UserFactory()

        form = OrganizationCreateForm(user=user, data={"phone": "invalid-phone"})

        form.is_valid()
        assert "phone" in form.errors

    def test_phone_valid_passes_validation(self, app: DjangoTestApp):
        user = UserFactory()

        form = OrganizationCreateForm(user=user, data={"phone": "+37061234567"})

        form.is_valid()
        assert "phone" not in form.errors


class TestOrganizationCreateForm:
    def test_organization_name_generated_prefix(self, app: DjangoTestApp):
        organization_instance = OrganizationFactory.build(name="test_org", kind=Organization.GOV)
        data = {field.name: getattr(organization_instance, field.name) for field in organization_instance._meta.fields}
        user = UserFactory(is_superuser=True)
        app.set_user(user)
        form = OrganizationCreateForm(user=user, data=data)
        assert form.is_valid()
        generated_name = form.cleaned_data["name"]
        assert generated_name == "datasets/gov/test-org/"


class TestRepresentativeCreateForm:
    def test_can_make_agreements_field_create_null_defaults_to_default_value(self, app: DjangoTestApp):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        app.set_user(user)

        form = RepresentativeCreateForm(
            data={
                "email": "example@example.com",
                "role": Representative.OPEN_DATA_MANAGER,
                "phone": "",
                "has_api_access": False,
                "regenerate_api_key": False,
                "can_make_agreements": None,  # Boolean field sent as None to form
            },
            user=user,
            object=organization,
        )

        assert form.is_valid(), form.errors
        assert form.cleaned_data["can_make_agreements"] is False
        representative = form.save(commit=False)
        assert representative.can_make_agreements is False

    def test_can_make_agreements_defaults_to_false_if_user_not_authorized_to_adjust_field(self, app: DjangoTestApp):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)
        user = UserFactory(is_viisp_login=False, viisp_company_code="<some_invalid_code>")
        app.set_user(user)

        form = RepresentativeCreateForm(
            data={
                "email": "example@example.com",
                "role": Representative.OPEN_DATA_MANAGER,
                "phone": "",
                "has_api_access": False,
                "regenerate_api_key": False,
                "can_make_agreements": None,  # User tries to force it
            },
            user=user,
            object=organization,
        )

        assert form.is_valid(), form.errors
        assert form.cleaned_data["can_make_agreements"] is False
        representative = form.save(commit=False)
        assert representative.can_make_agreements is False

    @pytest.mark.parametrize(
        "role,expected",
        [
            (Representative.RESOURCE_COORDINATOR, False),
            (Representative.OPEN_DATA_COORDINATOR, True),
        ],
    )
    def test_representative_create_can_make_agreements_field_access_for_coordinators(
        self, app: DjangoTestApp, role: str, expected: bool
    ):
        organization = OrganizationFactory(kind=Organization.GOV)
        user = UserFactory(
            is_viisp_login=True,
            viisp_company_code=organization.company_code,
        )
        app.set_user(user)

        RepresentativeFactory(
            user=user,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=role,
        )

        form = RepresentativeCreateForm(
            user=user,
            object=organization,
        )

        assert form.fields["can_make_agreements"].disabled is expected


class TestRepresentativeUpdateForm:
    def test_can_make_agreements_field_update_to_null_defaults_to_default_value(self, app: DjangoTestApp):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        content_type_user = ContentType.objects.get_for_model(User)
        representative = RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.OPEN_DATA_MANAGER,
            can_make_agreements=False,
            content_type=content_type_user,
            object_id=user.pk,
        )
        app.set_user(user)

        form = RepresentativeUpdateForm(
            data={
                "email": "example@example.com",
                "role": representative.role,
                "phone": "",
                "has_api_access": False,
                "regenerate_api_key": False,
                "can_make_agreements": None,  # Boolean field sent as None to form
            },
            user=user,
            object=organization,
            instance=representative,
        )

        assert form.is_valid()
        assert form.cleaned_data["can_make_agreements"] is False  # Should default to False in the end

    def test_can_make_agreements_defaults_to_false_if_user_is_not_authorized_to_adjust_the_field_value(
        self, app: DjangoTestApp
    ):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)
        user = UserFactory(is_viisp_login=False, viisp_company_code="<some_invalid_code>")
        content_type_user = ContentType.objects.get_for_model(User)
        representative = RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.OPEN_DATA_MANAGER,
            can_make_agreements=False,
            content_type=content_type_user,
            object_id=user.pk,
        )
        app.set_user(user)

        form = RepresentativeUpdateForm(
            data={
                "email": "example@example.com",
                "role": representative.role,
                "phone": "",
                "has_api_access": False,
                "regenerate_api_key": False,
                "can_make_agreements": None,  # Boolean field sent as None to form
            },
            user=user,
            object=organization,
            instance=representative,
        )

        assert form.is_valid()
        assert form.cleaned_data["can_make_agreements"] is False  # Should default to False in the end

    def test_open_data_coordinator_cannot_create_resource_manager(self, app: DjangoTestApp):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)

        user = UserFactory()
        app.set_user(user)

        RepresentativeFactory(
            user=user,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        form = RepresentativeCreateForm(
            data={
                "email": "invalid@example.com",
                "role": Representative.RESOURCE_MANAGER,
                "phone": "",
                "has_api_access": False,
                "regenerate_api_key": False,
                "can_make_agreements": None,
            },
            user=user,
            object=organization,
        )

        assert not form.is_valid()
        assert "role" in form.errors

    def test_open_data_coordinator_does_not_see_resource_roles(self, app: DjangoTestApp):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)

        user = UserFactory()
        app.set_user(user)

        RepresentativeFactory(
            user=user,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        form = RepresentativeCreateForm(
            user=user,
            object=organization,
        )

        role_choices = dict(form.fields["role"].choices)

        assert Representative.RESOURCE_MANAGER not in role_choices
        assert Representative.RESOURCE_COORDINATOR not in role_choices

        assert Representative.OPEN_DATA_MANAGER in role_choices
        assert Representative.OPEN_DATA_COORDINATOR in role_choices

    @pytest.mark.parametrize(
        "role,expected",
        [
            (Representative.RESOURCE_COORDINATOR, False),
            (Representative.OPEN_DATA_COORDINATOR, True),
        ],
    )
    def test_representative_update_can_make_agreements_field_access_for_coordinators(
        self, app: DjangoTestApp, role: str, expected: bool
    ):
        organization = OrganizationFactory(kind=Organization.GOV)
        user = UserFactory(
            is_viisp_login=True,
            viisp_company_code=organization.company_code,
        )
        app.set_user(user)

        RepresentativeFactory(
            user=user,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=role,
        )

        form = RepresentativeUpdateForm(
            user=user,
            object=organization,
        )

        assert form.fields["can_make_agreements"].disabled is expected


class TestPartnerRegisterForm:
    @pytest.mark.parametrize(
        "filename",
        [
            AGREEMENT_ONE_SIGNER,
            "test_form.pdf",
        ],
    )
    def test_request_form_accepted_file_types(self, agreements_dir: Path, filename: str):
        organization = OrganizationFactory()
        with open(agreements_dir / filename, "rb") as file:
            uploaded_file = SimpleUploadedFile(filename, file.read())

        form = PartnerRegisterForm(
            data={
                "organization": organization.pk,
                "coordinator_phone_number": "061234567",
            },
            files={"request_form": uploaded_file},
        )

        assert form.is_valid(), form.errors
