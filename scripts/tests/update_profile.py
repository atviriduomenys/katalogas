from playwright.sync_api import Page, Playwright, sync_playwright
import re

from utils import BASE_URL, login

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROFILE_DATA = {
    "first_name": "Super",
    "last_name": "Admin",
}


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def open_user_menu(page: Page) -> None:
    """Open the user dropdown menu (handles 'None None' display name)."""
    page.locator("a").filter(has_text=re.compile(r"^None None$")).click()


def go_to_profile(page: Page) -> None:
    """Navigate to the profile page."""
    open_user_menu(page)
    page.get_by_role("link", name="Profilis").click()
    page.wait_for_load_state("networkidle")


def edit_profile(page: Page, first_name: str, last_name: str) -> None:
    """Update the user's first and last name."""
    page.get_by_role("link", name="Keisti duomenis").click()
    page.get_by_role("textbox", name="Vardas *").fill(first_name)
    page.get_by_role("textbox", name="Pavardė *").fill(last_name)
    page.get_by_role("button", name="Patvirtinti").click()
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    page.goto(BASE_URL)
    login(page)
    go_to_profile(page)
    edit_profile(page, PROFILE_DATA["first_name"], PROFILE_DATA["last_name"])

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
