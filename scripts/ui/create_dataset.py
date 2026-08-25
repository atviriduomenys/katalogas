"""Create one dataset under Org1.

Expects Org1 to exist - create_organization.py makes it.
"""

from playwright.sync_api import Playwright, sync_playwright
from utils import browser_page


def run(playwright: Playwright) -> None:
    with browser_page(playwright) as page:
        page.get_by_role("link", name="Organizacijos").click()
        page.get_by_role("link", name="Org1").click()
        page.locator("#main-content").get_by_role("link", name="Duomenų ištekliai").click()
        page.get_by_role("link", name="Pridėti duomenų išteklių").click()
        page.get_by_text("Koncepcinė klasė, aprašanti").click()
        page.get_by_role("button", name="Toliau").click()
        page.get_by_role("textbox", name="Pavadinimas *").click()
        page.get_by_role("textbox", name="Pavadinimas *").fill("Duom rink 1")
        page.get_by_role("textbox", name="Pavadinimas *").press("Tab")
        page.get_by_role("textbox", name="Kodinis pavadinimas").fill("datasets/org/org1/dr1")
        page.get_by_role("textbox", name="Kodinis pavadinimas").press("Tab")
        page.get_by_role("textbox", name="Aprašymas *").fill("Duom rink 1 pilnas aprašymas")
        page.get_by_label("Atnaujinimo dažnumas *").select_option("15")
        page.get_by_role("button", name="Sukurti").click()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
