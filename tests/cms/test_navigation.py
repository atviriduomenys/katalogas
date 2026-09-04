import pytest
from cms.api import create_page, create_page_content
from cms.models import PageContent

from vitrina.templatetags.navigation_tags import _published_nav_page_ids, _render_menu
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


# `_render_menu` is what `show_menu` calls on a cache miss. Going through it
# directly keeps these tests about the menu itself rather than about caching,
# which `test_navigation_tags.py` covers.


@pytest.mark.django_db
def test_root_pages_are_listed(user):
    first = make_page("Pirmas", "pirmas", user)
    second = make_page("Antras", "antras", user)

    html = _render_menu("lt")

    assert first.get_menu_title() in html
    assert second.get_menu_title() in html


@pytest.mark.django_db
def test_children_are_listed_under_their_parent(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child = make_page("Vaikas", "vaikas", user, parent=parent)

    html = _render_menu("lt")

    # Nested in the parent's dropdown, and not repeated as a top level entry.
    assert "navbar-dropdown" in html
    assert html.count(f'href="{child.get_absolute_url()}"') == 1


@pytest.mark.django_db
def test_draft_page_is_hidden(user):
    published = make_page("Matomas", "matomas", user)
    draft = make_page("Juodraštis", "juodrastis", user, published=False)

    html = _render_menu("lt")

    assert published.get_menu_title() in html
    assert "Juodraštis" not in html
    assert draft.pk not in list(_published_nav_page_ids("lt"))


@pytest.mark.django_db
def test_draft_child_is_hidden(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child = make_page("Vaikas", "vaikas", user, parent=parent)
    make_page("Juodraštis", "juodrastis", user, parent=parent, published=False)

    html = _render_menu("lt")

    assert child.get_menu_title() in html
    assert "Juodraštis" not in html


@pytest.mark.django_db
def test_page_outside_navigation_is_hidden(user):
    visible = make_page("Matomas", "matomas", user)
    make_page("Paslėptas", "pasleptas", user, in_navigation=False)

    html = _render_menu("lt")

    assert visible.get_menu_title() in html
    assert "Paslėptas" not in html


@pytest.mark.django_db
def test_leaf_page_renders_as_a_plain_item(user):
    make_page("Vienas", "vienas", user)

    html = _render_menu("lt")

    assert "Vienas" in html
    assert "navbar-dropdown" not in html


@pytest.mark.django_db
def test_child_renders_with_its_own_title_and_url(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child = make_page("Vaikas", "vaikas", user, parent=parent)

    html = _render_menu("lt")

    # The menu yields Page objects; reading the title or the URL off a menu
    # node attribute would render both of these empty.
    assert "navbar-dropdown" in html
    assert child.get_menu_title() in html
    assert f'href="{child.get_absolute_url()}"' in html


@pytest.mark.django_db
def test_page_published_in_two_languages_yields_one_id(user):
    page = make_page("Vienas", "vienas", user)
    create_page_content(language="en", title="One", page=page, created_by=user, in_navigation=True)
    PageContent.admin_manager.filter(page=page, language="en").first().versions.first().publish(user)

    ids = list(_published_nav_page_ids("lt"))

    # There is one PageContent per language and the versioning manager joins to
    # the version table, so without distinct() the same id comes back twice.
    assert ids == [page.pk]


@pytest.mark.django_db
def test_page_published_only_in_another_language_is_hidden(user):
    visible = make_page("Matomas", "matomas", user)
    english_only = make_page("English only", "english-only", user, published=False)
    content = create_page_content(
        language="en", title="English only", page=english_only, created_by=user, in_navigation=True
    )
    content.versions.first().publish(user)

    html = _render_menu("lt")

    # The menu is cached per language, so it must be built per language too -
    # otherwise this points Lithuanian readers at a page they cannot see.
    assert visible.get_menu_title() in html
    assert "English only" not in html
    assert english_only.pk not in list(_published_nav_page_ids("lt"))
    assert english_only.pk in list(_published_nav_page_ids("en"))


@pytest.mark.django_db
def test_dropdown_children_are_ordered(user):
    parent = make_page("Tėvinis", "tevinis", user)
    first = make_page("Aaa", "aaa", user, parent=parent)
    second = make_page("Bbb", "bbb", user, parent=parent)
    third = make_page("Ccc", "ccc", user, parent=parent)

    # Rewriting a row is enough to change the order the database hands back.
    second.save()

    html = _render_menu("lt")
    positions = [html.index(page.get_menu_title()) for page in (first, second, third)]

    assert positions == sorted(positions)
