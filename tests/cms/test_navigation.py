import pytest
from cms.api import create_page
from cms.models import PageContent
from django.template import Context, Template

from vitrina.templatetags.navigation_tags import show_menu
from vitrina.users.factories import UserFactory

TEMPLATE = "pages/page.html"


@pytest.fixture
def user():
    return UserFactory()


def make_page(title, slug, user, parent=None, published=True, in_navigation=True):
    """Create a page, published and in navigation unless told otherwise."""
    page = create_page(
        title=title,
        template=TEMPLATE,
        language="lt",
        slug=slug,
        created_by=user,
        parent=parent,
        in_navigation=in_navigation,
    )
    if published:
        content = PageContent.admin_manager.filter(page=page, language="lt").first()
        content.versions.first().publish(user)
    return page


def render_menu():
    return Template("{% load navigation_tags %}{% show_menu %}").render(Context())


@pytest.mark.django_db
def test_root_pages_are_listed(user):
    first = make_page("Pirmas", "pirmas", user)
    second = make_page("Antras", "antras", user)

    assert list(show_menu()["pages"]) == [first, second]


@pytest.mark.django_db
def test_children_are_listed_under_their_parent(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child = make_page("Vaikas", "vaikas", user, parent=parent)

    pages = show_menu()["pages"]

    # Children are nested, not repeated as top level entries.
    assert list(pages) == [parent]
    assert list(pages[parent]) == [child]


@pytest.mark.django_db
def test_draft_page_is_hidden(user):
    published = make_page("Matomas", "matomas", user)
    draft = make_page("Juodraštis", "juodrastis", user, published=False)

    pages = show_menu()["pages"]

    assert published in pages
    assert draft not in pages


@pytest.mark.django_db
def test_draft_child_is_hidden(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child = make_page("Vaikas", "vaikas", user, parent=parent)
    draft_child = make_page("Juodraštis", "juodrastis", user, parent=parent, published=False)

    children = list(show_menu()["pages"][parent])

    assert children == [child]
    assert draft_child not in children


@pytest.mark.django_db
def test_page_outside_navigation_is_hidden(user):
    visible = make_page("Matomas", "matomas", user)
    hidden = make_page("Paslėptas", "pasleptas", user, in_navigation=False)

    pages = show_menu()["pages"]

    assert visible in pages
    assert hidden not in pages


@pytest.mark.django_db
def test_leaf_page_renders_as_a_plain_item(user):
    make_page("Vienas", "vienas", user)

    html = render_menu()

    assert "Vienas" in html
    assert "navbar-dropdown" not in html


@pytest.mark.django_db
def test_child_renders_with_its_own_title_and_url(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child = make_page("Vaikas", "vaikas", user, parent=parent)

    html = render_menu()

    # `show_menu` yields Page objects; reading the title or the URL off a menu
    # node attribute would render both of these empty.
    assert "navbar-dropdown" in html
    assert child.get_menu_title() in html
    assert 'href="%s"' % child.get_absolute_url() in html
