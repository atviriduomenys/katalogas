import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:8000/")
    page.get_by_role("link", name="Prisijungti").click()
    page.get_by_role("textbox", name="El. paštas *").click()
    page.get_by_role("textbox", name="El. paštas *").fill("superadmin@aa.lt")
    page.get_by_role("textbox", name="El. paštas *").press("Tab")
    page.get_by_role("textbox", name="Slaptažodis *").fill("Liabas.2345")
    page.get_by_role("textbox", name="Slaptažodis *").press("Enter")
    page.get_by_role("textbox", name="Slaptažodis *").click()
    page.get_by_role("textbox", name="Slaptažodis *").press("Shift+Home")
    page.get_by_role("textbox", name="Slaptažodis *").fill("Liabas.12345")
    page.get_by_role("textbox", name="Slaptažodis *").press("Enter")
    page.get_by_role("button", name="Prisijungti").click()
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

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
