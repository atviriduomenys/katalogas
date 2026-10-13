from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import AreaOfManagementFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.helpers import get_or_create_parent_org
from vitrina.orgs.models import Organization
from vitrina.users.factories import UserFactory


def _ministry_with_child():
    jurisdiction = AreaOfManagementFactory(id=101, name_lt="Sveikatos apsaugos ministerija")
    parent = OrganizationFactory(title="Sveikatos  apsaugos ministerija", jurisdiction=jurisdiction)
    child = OrganizationFactory(title="Higienos institutas", jurisdiction=jurisdiction)
    Organization.objects.get(pk=child.pk).move(Organization.objects.get(pk=parent.pk), "sorted-child")
    return jurisdiction, Organization.objects.get(pk=parent.pk), Organization.objects.get(pk=child.pk)


def test_parent_found_by_jurisdiction_when_title_differs():
    jurisdiction, parent, _ = _ministry_with_child()

    assert get_or_create_parent_org(jurisdiction) == parent
    assert Organization.objects.filter(title__contains="apsaugos ministerija").count() == 1


def test_parent_found_by_exact_title_before_jurisdiction():
    jurisdiction = AreaOfManagementFactory(id=102, name_lt="Savivaldybės")
    OrganizationFactory(title="Kita grupė", jurisdiction=jurisdiction)
    by_title = OrganizationFactory(title="Savivaldybės")

    assert get_or_create_parent_org(jurisdiction) == by_title


def test_save_without_jurisdiction_change_keeps_parent(app: DjangoTestApp):
    _, parent, child = _ministry_with_child()
    app.set_user(UserFactory(is_superuser=True))

    form = app.get(reverse("organization-change", kwargs={"pk": child.pk})).forms["organization-form"]
    form["description"] = "changed"
    form.submit()

    child.refresh_from_db()
    assert child.description == "changed"
    assert child.get_parent() == parent
    assert Organization.objects.filter(title__contains="apsaugos ministerija").count() == 1


def test_save_with_jurisdiction_change_moves_org(app: DjangoTestApp):
    _, parent, child = _ministry_with_child()
    other = AreaOfManagementFactory(id=103, name_lt="Kultūros ministerija")
    other_parent = OrganizationFactory(title="Kultūros ministerija", jurisdiction=other)
    app.set_user(UserFactory(is_superuser=True))

    form = app.get(reverse("organization-change", kwargs={"pk": child.pk})).forms["organization-form"]
    form["jurisdiction"] = other.pk
    form.submit()

    child.refresh_from_db()
    assert child.get_parent() == other_parent
