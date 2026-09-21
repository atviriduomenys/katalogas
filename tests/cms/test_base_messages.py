import pytest
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import RequestFactory


class FakeToolbar:
    """A staff toolbar stub: the two methods `{% cms_toolbar %}` calls."""

    def __init__(self, *, edit_mode_active):
        self.show_toolbar = True
        self.edit_mode_active = edit_mode_active

    def init_toolbar(self, request, **kwargs):
        pass

    def render_with_structure(self, context, nodelist):
        return nodelist.render(context)


def render(edit_mode_active):
    request = RequestFactory().get("/")
    request.toolbar = FakeToolbar(edit_mode_active=edit_mode_active)
    return render_to_string(
        "base.html",
        {"messages": [Message(20, "Įrašas išsaugotas")], "request": request},
        request=request,
    )


@pytest.mark.django_db
def test_staff_still_see_flash_messages_outside_the_editor():
    """show_toolbar is true for every staff user, so hiding messages on it hides them site-wide.

    Never iterated, they are never marked read either, and come back on every request.
    """
    assert "Įrašas išsaugotas" in render(edit_mode_active=False)


@pytest.mark.django_db
def test_messages_step_aside_for_the_editing_toolbar():
    assert "Įrašas išsaugotas" not in render(edit_mode_active=True)


@pytest.mark.django_db
def test_the_page_carries_no_template_comment_markup():
    """`{# #}` is single-line only: a multi-line one goes out as page text."""
    assert "{#" not in render(edit_mode_active=False)
