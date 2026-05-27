from playwright.sync_api import Page

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"

CREDENTIALS = {
    "email": "superadmin@aa.lt",
    "password": "Liabas.12345",
}


# ---------------------------------------------------------------------------
# Common step functions
# ---------------------------------------------------------------------------

def login(page: Page, email: str = CREDENTIALS["email"], password: str = CREDENTIALS["password"]) -> None:
    """Log in using email and password."""
    page.get_by_role("link", name="Prisijungti").click()
    page.get_by_role("textbox", name="El. paštas *").fill(email)
    page.get_by_role("textbox", name="Slaptažodis *").fill(password)
    page.get_by_role("button", name="Prisijungti").click()
    page.wait_for_load_state("networkidle")
