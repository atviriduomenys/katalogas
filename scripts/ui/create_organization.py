"""Create organizations, numbered from VITRINA_UI_ORG_START.

Starts from an empty portal; nothing has to exist first.
"""

import itertools
import os

from playwright.sync_api import Page, Playwright, sync_playwright
from utils import BASE_URL, browser_page

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Organization name and slug are unique, so a second run over the same database
# collides on Org1. Set VITRINA_UI_ORG_START past whatever is already there.
ORGANIZATION_COUNT = 3

_org_counter = itertools.count(start=int(os.environ.get("VITRINA_UI_ORG_START", "1")))


def generate_organization_data():
    """Generate unique organization data for each call."""
    n = next(_org_counter)
    n_padded = f"{n:02d}"
    n_phone = f"{n:03d}"

    return {
        "search_query": f"123{n_padded}",
        "reg_number": f"111{n_phone}",
        "name": f"Org{n}",
        "slug": f"org{n}",
        "type": "com",
        "logo": f"{n_padded}.png",
        "website": f"http://org{n}.lt",
        "email": f"info@org{n}.lt",
        "phone": f"+370603{n_phone}",
        "address": f"Kauno g. {n}, Vilnius",
        "description": f"Org{n} pilnas aprašymas",
        "jurisdiction": "19",
    }


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def go_to_organizations(page: Page) -> None:
    """Navigate to the Organizations list from the homepage."""
    page.goto(f"{BASE_URL}/organizations/")
    page.wait_for_load_state("networkidle")


def start_new_organization(page: Page, search_query: str) -> None:
    """Click 'New organization' and search for an existing org to base it on."""
    page.get_by_role("link", name="Nauja organizacija").click()
    page.get_by_role("combobox", name="Paieška ribojama, įveskite").fill(search_query)
    page.get_by_role("button", name="Tęsti").click()
    page.wait_for_load_state("networkidle")


def fill_organization_form(page: Page, org: dict) -> None:
    """Fill in the new organization form fields."""
    page.get_by_role("textbox", name="Registracijos numeris *").fill(org["reg_number"])
    page.get_by_role("textbox", name="Pavadinimas *", exact=True).fill(org["name"])
    page.get_by_role("textbox", name="Kodinis pavadinimas *").fill(org["slug"])
    page.get_by_label("Tipas *").select_option(org["type"])
    page.get_by_label("Valdymo sritis *").select_option(org["jurisdiction"])
    page.get_by_role("textbox", name="Tinklalapis").fill(org["website"])
    page.get_by_role("textbox", name="Elektroninis paštas *").fill(org["email"])
    page.get_by_role("textbox", name="Telefono numeris *").fill(org["phone"])
    page.get_by_role("textbox", name="Adresas *").fill(org["address"])
    page.get_by_role("textbox", name="Aprašymas").fill(org["description"])
    page.wait_for_load_state("networkidle")


def submit_organization_form(page: Page) -> None:
    """Submit the organization creation form."""
    page.get_by_role("button", name="Sukurti").click()
    page.wait_for_load_state("networkidle")


def create_organization(page: Page, org: dict) -> None:
    """Run the full creation flow for a single organization."""
    print(f"Creating organization: {org['name']}...")
    start_new_organization(page, org["search_query"])
    fill_organization_form(page, org)
    submit_organization_form(page)
    print(f"✅ {org['name']} created successfully.")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(playwright: Playwright) -> None:
    with browser_page(playwright) as page:
        for _ in range(ORGANIZATION_COUNT):
            go_to_organizations(page)
            organization = generate_organization_data()
            create_organization(page, organization)


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
