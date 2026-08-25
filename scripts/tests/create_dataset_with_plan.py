import re

from playwright.sync_api import Playwright, sync_playwright
from utils import BASE_URL, login


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(BASE_URL)
    login(page)
    page.get_by_role("link", name="Organizacijos").click()
    page.get_by_role("link", name="Org1").click()
    page.locator("#main-content").get_by_role("link", name="Duomenų ištekliai").click()
    page.get_by_role("link", name="Pridėti duomenų išteklių").click()
    page.get_by_text("Koncepcinė klasė, aprašanti").click()
    page.get_by_role("button", name="Toliau").click()
    page.get_by_role("textbox", name="Pavadinimas *").click()
    page.get_by_role("textbox", name="Pavadinimas *").click()
    page.get_by_role("textbox", name="Pavadinimas *").fill("Duom rink 1")
    page.get_by_role("textbox", name="Pavadinimas *").press("Tab")
    page.get_by_role("textbox", name="Kodinis pavadinimas").fill("datasets/org/org1/dr1")
    page.get_by_role("textbox", name="Kodinis pavadinimas").press("Tab")
    page.get_by_role("textbox", name="Aprašymas *").fill("Duom rink 1 pilnas aprašymas")
    page.get_by_label("Atnaujinimo dažnumas *").select_option("15")
    page.get_by_role("button", name="Sukurti").click()
    page.locator("h1").get_by_text("Duom rink").click()
    page.get_by_role("link", name="Planas").click()
    page.get_by_role("link", name="Įtraukti į planą").click()
    page.get_by_role("textbox", name="Aprašymas").click()
    page.get_by_role("textbox", name="Aprašymas").click()
    page.get_by_role("textbox", name="Aprašymas").fill("Plano 1 veiksmo 1 aprašymas")
    page.get_by_role("textbox", name="Įgyvendinimo terminas").fill("2026-05-29")
    page.locator("#plan-form").get_by_role("button", name="Įtraukti").click()
    page.get_by_role("link", name="Įtraukti į planą").click()
    page.get_by_role("textbox", name="Aprašymas").click()
    page.get_by_role("textbox", name="Aprašymas").fill("Org 1 planas 2 aprašymas\n")
    page.get_by_role("textbox", name="Pavadinimas *").click()
    page.get_by_role("textbox", name="Pavadinimas *").press("Shift+Home")
    page.get_by_role("textbox", name="Pavadinimas *").fill("Org 1 planas 2")
    page.get_by_role("textbox", name="Įgyvendinimo terminas").fill("2026-05-31")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("#plan-form").get_by_role("button", name="Įtraukti").click()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("link", name="Įtraukti į planą").click()
    # The id differs per database, so read it from wherever we ended up. Guessing
    # would open some unrelated dataset and hide whatever went wrong here.
    match = re.search(r"/datasets/(\d+)/", page.url)
    if not match:
        raise SystemExit(f"Expected to be on a dataset page, but the url is {page.url}")
    page.goto(f"{BASE_URL}/datasets/{match.group(1)}/plans/")

    # ---------------------
    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
