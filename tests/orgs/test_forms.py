from django.urls import reverse

from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.forms import OrganizationUpdateForm, OrganizationCreateForm
from django_webtest import DjangoTestApp

from vitrina.orgs.models import Organization
from vitrina.users.factories import UserFactory


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
