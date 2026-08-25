import os
from contextlib import contextmanager

from playwright.sync_api import Page, Playwright

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Trailing slash stripped: every caller builds urls as f"{BASE_URL}/...".
BASE_URL = os.environ.get("VITRINA_UI_URL", "http://localhost:8000").rstrip("/")

EMAIL_VAR = "VITRINA_UI_EMAIL"
PASSWORD_VAR = "VITRINA_UI_PASSWORD"

# These scripts are meant to be watched, so the browser is visible and slowed
# down by default. VITRINA_UI_HEADLESS=1 turns that off when the point is only
# to get content into the database.
# The filer folder create_blog_posts.py makes and the other two read from.
IMAGE_FOLDER = "Skaiciai"

HEADLESS = os.environ.get("VITRINA_UI_HEADLESS") == "1"
SLOW_MO = 0 if HEADLESS else 500
VIEWPORT = {"width": 1920, "height": 1080}


def _credential(name: str) -> str:
    """Read one credential, or stop with an explanation.

    Without this the script would open a browser, type an empty password and
    fail somewhere further in, on a selector that has nothing to do with the
    real problem.
    """
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is not set. These scripts drive the portal as a real user, so export both:\n"
            f"  export {EMAIL_VAR}=...\n"
            f"  export {PASSWORD_VAR}=..."
        )
    return value


# ---------------------------------------------------------------------------
# Common step functions
# ---------------------------------------------------------------------------


def login(page: Page, email: str | None = None, password: str | None = None) -> None:
    """Log in using email and password, taken from the environment by default."""
    email = email or _credential(EMAIL_VAR)
    password = password or _credential(PASSWORD_VAR)

    page.get_by_role("link", name="Prisijungti").click()
    page.get_by_role("textbox", name="El. paštas *").fill(email)
    page.get_by_role("textbox", name="Slaptažodis *").fill(password)
    page.get_by_role("button", name="Prisijungti").click()
    page.wait_for_load_state("networkidle")


@contextmanager
def browser_page(playwright: Playwright):
    """Open a page on the portal, logged in, and close everything afterwards.

    Every script wants the same thing, and before this each one launched the
    browser its own way - some slowed down, some not, some with a viewport
    wide enough for the admin and some not.
    """
    browser = playwright.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
    context = browser.new_context(viewport=VIEWPORT)
    page = context.new_page()
    page.goto(BASE_URL)
    login(page)
    try:
        yield page
    finally:
        context.close()
        browser.close()
