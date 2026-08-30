import pytest
from cms.api import add_plugin, create_page, create_page_content
from cms.models import PageContent

from vitrina.cms.cms_plugins import SideMenuPlugin
from vitrina.users.factories import UserFactory

TEMPLATE = "pages/page_with_side_menu.html"


@pytest.fixture
def user():
    return UserFactory()


def make_page(title, slug, user, parent=None, published=True):
    """Create a page using the side menu template, published unless told otherwise."""
    page = create_page(
        title=title,
        template=TEMPLATE,
        language="lt",
        slug=slug,
        created_by=user,
        parent=parent,
        in_navigation=True,
    )
    if published:
        content = PageContent.admin_manager.filter(page=page, language="lt").first()
        content.versions.first().publish(user)
    return page


def render_side_menu(page, user):
    """Put a SideMenuPlugin on the page and return the context it renders with."""
    content = PageContent.admin_manager.filter(page=page, language="lt").first()
    placeholder = content.rescan_placeholders()["side_menu"]
    instance = add_plugin(placeholder, "SideMenuPlugin", "lt")
    return SideMenuPlugin().render({}, instance, placeholder)


@pytest.mark.django_db
def test_page_with_children_lists_its_children(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child_a = make_page("Vaikas A", "vaikas-a", user, parent=parent)
    child_b = make_page("Vaikas B", "vaikas-b", user, parent=parent)

    context = render_side_menu(parent, user)

    assert context["parent"] == parent
    assert list(context["children"]) == [child_a, child_b]


@pytest.mark.django_db
def test_unpublished_children_are_hidden(user):
    parent = make_page("Tėvinis", "tevinis", user)
    published_child = make_page("Matomas", "matomas", user, parent=parent)
    draft_child = make_page("Juodraštis", "juodrastis", user, parent=parent, published=False)

    context = render_side_menu(parent, user)

    children = list(context["children"])
    assert published_child in children
    assert draft_child not in children


@pytest.mark.django_db
def test_leaf_page_lists_its_siblings(user):
    parent = make_page("Tėvinis", "tevinis", user)
    leaf = make_page("Lapas", "lapas", user, parent=parent)
    sibling = make_page("Brolis", "brolis", user, parent=parent)

    context = render_side_menu(leaf, user)

    assert context["parent"] == parent
    children = list(context["children"])
    assert leaf in children
    assert sibling in children


@pytest.mark.django_db
def test_leaf_page_does_not_list_unpublished_siblings(user):
    parent = make_page("Tėvinis", "tevinis", user)
    leaf = make_page("Lapas", "lapas", user, parent=parent)
    draft_sibling = make_page("Juodraštis", "juodrastis", user, parent=parent, published=False)

    context = render_side_menu(leaf, user)

    assert draft_sibling not in list(context["children"])


@pytest.mark.django_db
def test_page_whose_children_are_all_drafts_falls_back_to_siblings(user):
    root = make_page("Šaknis", "saknis", user)
    page = make_page("Puslapis", "puslapis", user, parent=root)
    sibling = make_page("Brolis", "brolis", user, parent=root)
    make_page("Paslėptas", "pasleptas", user, parent=page, published=False)

    context = render_side_menu(page, user)

    # The only child is a draft, so the menu shows the section the page sits in.
    assert context["parent"] == root
    assert sibling in list(context["children"])


@pytest.mark.django_db
def test_children_published_only_in_another_language_are_hidden(user):
    parent = make_page("Tėvinis", "tevinis", user)
    child = make_page("Vaikas", "vaikas", user, parent=parent)
    english_only = make_page("English only", "english-only", user, parent=parent, published=False)
    content = create_page_content(language="en", title="English only", page=english_only, created_by=user)
    content.versions.first().publish(user)

    context = render_side_menu(parent, user)

    children = list(context["children"])
    assert child in children
    assert english_only not in children


@pytest.mark.django_db
def test_no_empty_heading_when_the_parent_is_not_published(user):
    """The heading links to the parent, so with no parent there is nothing to link.

    Rendering it anyway leaves <a href=""> with no text, which sends the reader
    back to the page they are already on.
    """
    from django.template.loader import render_to_string

    root = make_page("Šaknis", "saknis", user, published=False)
    page = make_page("Puslapis", "puslapis", user, parent=root)
    sibling = make_page("Brolis", "brolis", user, parent=root)

    context = render_side_menu(page, user)
    assert context["parent"] is None
    assert sibling in list(context["children"])

    html = render_to_string("pages/side_menu.html", context)
    assert 'href=""' not in html
