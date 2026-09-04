from __future__ import annotations

import datetime
import os
import shutil

import pytest
from django.conf import settings
from django.db import connections


# Live database connection: points at the database the running application
# (docker compose) actually uses, so seeded objects are visible to the browser
# and "skip if exists" checks can be performed.  We never use the default
# (test) database for these end-to-end tests.
LIVE_DB = {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": os.environ.get("E2E_DB_HOST", "127.0.0.1"),
    "PORT": os.environ.get("E2E_DB_PORT", "5432"),
    "NAME": os.environ.get("E2E_DB_NAME", "adp-dev"),
    "USER": os.environ.get("E2E_DB_USER", "adp"),
    "PASSWORD": os.environ.get("E2E_DB_PASSWORD", "secret"),
    "ATOMIC_REQUESTS": False,
}


@pytest.fixture(scope="session", autouse=True)
def configure_live_db(django_db_setup):
    # Point the default connection at the database the running application
    # (docker compose) uses, so seeded objects are visible to the browser and
    # "skip if exists" checks work.  pytest-django still creates its own
    # `test_*` database, which we simply never use.
    # Merge onto the existing settings dict so Django's DB defaults
    # (TIME_ZONE, etc.) are preserved.
    live = dict(settings.DATABASES["default"])
    live.update(LIVE_DB)
    settings.DATABASES["default"] = live
    connections.databases["default"] = live
    yield


def today_suffix() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


@pytest.fixture
def login_user():
    """Return a helper that logs a user in through the custom /login/ form."""

    def _login(page, email: str, password: str = "test") -> None:
        page.goto("/login/")
        page.wait_for_selector('input[name="username"]')
        page.fill('input[name="username"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

    return _login


def select2(page, field_name: str, value: str, by_label: bool = True, multiple: bool = False) -> None:
    """Pick an option in a django-select2 widget by opening it and searching."""
    container = page.locator(f'select[name="{field_name}"] ~ .select2-container .select2-selection')
    container.click()
    search = page.locator(".select2-search__field")
    search.fill(value)
    page.wait_for_selector(".select2-results__option--highlighted", timeout=8000)
    page.locator(".select2-results__option--highlighted").first.click()
    if not multiple:
        page.wait_for_selector(".select2-container--below", timeout=8000)


def submit_form(page) -> None:
    page.click('#dataset-form button[type="submit"], form#dataset-form input[type="submit"]')
    page.wait_for_load_state("networkidle")


def add_tag(page, field_name: str, value: str) -> None:
    """Attach an existing tag to a tagulous/tagwidget field.

    On a normally-rendered page the widget is a select2; on htmx-swapped
    wizard fragments select2 may not be initialized, in which case the raw
    text input is used directly.
    """
    sel = (
        f'input[name="{field_name}"] ~ .select2-container .select2-selection, '
        f'select[name="{field_name}"] ~ .select2-container .select2-selection'
    )
    if page.locator(sel).count():
        container = page.locator(sel)
        container.click()
        search = page.locator(".select2-search__field")
        search.fill(value)
        page.wait_for_selector(".select2-results__option", timeout=8000)
        page.locator(".select2-results__option").first.click()
        page.wait_for_timeout(300)
    else:
        page.fill(f'input[name="{field_name}"]', value)
        page.wait_for_timeout(200)




@pytest.fixture(scope="session", autouse=True)
def _unblock_db_access(django_db_blocker):
    # These end-to-end tests run against a live database and use module-scoped
    # fixtures (e.g. `seed`) that need DB access before the per-test
    # `django_db` marker unblocks it. Unblock DB access for the whole session.
    with django_db_blocker.unblock():
        yield


@pytest.fixture(scope="session")
def browser_type_launch_args(pytestconfig):
    chromium = shutil.which("chromium") or shutil.which("chromium-browser")
    args = {"executable_path": chromium, "headless": True}
    if pytestconfig.getoption("--headed", default=False):
        args["headless"] = False
    return args
