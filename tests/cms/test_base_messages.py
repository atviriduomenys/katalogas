import pytest
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import RequestFactory


class FakeToolbar:
    """A staff toolbar, as cms builds one for every request a staff user makes.

    The two methods are what `{% cms_toolbar %}` calls once show_toolbar is on;
    rendering the real toolbar needs a request cycle this test has no use for.
    """

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
    """`show_toolbar` is true for every staff user on every page.

    Hiding the messages whenever it is true takes them away site-wide - a saved
    dataset, a rejected form, a changed password - and because the list is then
    never iterated, Django never marks them read and they come back on every
    following request.
    """
    assert "Įrašas išsaugotas" in render(edit_mode_active=False)


@pytest.mark.django_db
def test_messages_step_aside_for_the_editing_toolbar():
    assert "Įrašas išsaugotas" not in render(edit_mode_active=True)
