import os

from playwright.sync_api import Page

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("VITRINA_UI_URL", "http://localhost:8000")

EMAIL_VAR = "VITRINA_UI_EMAIL"
PASSWORD_VAR = "VITRINA_UI_PASSWORD"


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
