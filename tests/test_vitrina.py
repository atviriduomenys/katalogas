import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import CategoryFactory
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_home(app: DjangoTestApp):
    resp = app.get("/")

    assert resp.status == "200 OK"
    assert resp.context["counts"] == {
        "dataset": 1,
        "organization": 1,
        "project": 0,
        "coordinators": 0,
        "managers": 0,
        "users": 1,
    }

    assert [list(elem.stripped_strings) for elem in resp.html.select("a.stats")] == [
        ["1", "Organizacijos"],
        ["1", "Duomenų ištekliai"],
        ["0", "Panaudojimo atvejai"],
        # ['0', 'Koordinatoriai'],
        # ['0', 'Tvarkytojai'],
        # ['0', 'Naudotojai'],
    ]


@pytest.mark.django_db
def test_home_separates_featured_and_thematic_categories(app: DjangoTestApp):
    featured = CategoryFactory(title="Featured category", featured=True)
    thematic = CategoryFactory(title="Thematic category", featured=False, thematic=True)

    resp = app.get("/")

    assert resp.status == "200 OK"
    assert list(resp.context["categories"]) == [featured]
    assert list(resp.context["thematic_categories"]) == [thematic]
    assert "Teminiai duomenų ištekliai" in resp.text

    sveikata_tile = resp.html.select_one('a[href="https://duomenys.stat.gov.lt/sveikatos-duomenys/"]')
    assert sveikata_tile is not None
    assert sveikata_tile["target"] == "_blank"
    assert "noopener" in sveikata_tile["rel"]
    assert sveikata_tile.select_one("i.fa-arrow-up-right-from-square") is not None


@pytest.mark.django_db
def test_request_create_link(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resp = app.get("/")
    resp = resp.click(linkid="request-create")
    assert resp.request.path == reverse("request-create")
