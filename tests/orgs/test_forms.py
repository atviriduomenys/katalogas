from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.forms import OrganizationUpdateForm, OrganizationCreateForm, RepresentativeUpdateForm, \
    RepresentativeCreateForm
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
                "role": Representative.MANAGER,
                "phone": "",
                "has_api_access": False,
                "regenerate_api_key": False,
                "can_write": False,
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
                "role": Representative.MANAGER,
                "phone": "",
                "has_api_access": False,
                "regenerate_api_key": False,
                "can_write": False,
                "can_make_agreements": None,  # User tries to force it
            },
            user=user,
            object=organization,
        )

        assert form.is_valid(), form.errors
        assert form.cleaned_data["can_make_agreements"] is False
        representative = form.save(commit=False)
        assert representative.can_make_agreements is False


class TestRepresentativeUpdateForm:
    def test_can_make_agreements_field_update_to_null_defaults_to_default_value(self, app: DjangoTestApp):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        content_type_user = ContentType.objects.get_for_model(User)
        representative = RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.MANAGER,
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
                "can_write": False,
                "can_make_agreements": None,  # Boolean field sent as None to form
            },
            user=user,
            object=organization,
            instance=representative,
        )

        assert form.is_valid()
        assert form.cleaned_data["can_make_agreements"] is False  # Should default to False in the end


    def test_can_make_agreements_defaults_to_false_if_user_is_not_authorized_to_adjust_the_field_value(self, app: DjangoTestApp):
        organization = OrganizationFactory(name="Org", kind=Organization.GOV)
        user = UserFactory(is_viisp_login=False, viisp_company_code="<some_invalid_code>")
        content_type_user = ContentType.objects.get_for_model(User)
        representative = RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.MANAGER,
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
                "can_write": False,
                "can_make_agreements": None,  # Boolean field sent as None to form
            },
            user=user,
            object=organization,
            instance=representative,
        )

        assert form.is_valid()
        assert form.cleaned_data["can_make_agreements"] is False  # Should default to False in the end
