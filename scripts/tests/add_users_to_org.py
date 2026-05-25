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
    page.get_by_role("textbox", name="Slaptažodis *").fill("Liabs.12345")
    page.get_by_role("textbox", name="Slaptažodis *").press("Enter")
    page.get_by_role("button", name="Prisijungti").click()
    page.get_by_role("textbox", name="Slaptažodis *").click()
    page.get_by_role("textbox", name="Slaptažodis *").fill("Liabas.12345")
    page.get_by_role("textbox", name="Slaptažodis *").press("Enter")
    page.get_by_role("button", name="Prisijungti").click()
    page.locator("#adp-landing-numbers div").filter(has_text="Organizacijos").click()
    page.get_by_role("link", name="Org1").click()
    page.get_by_role("link", name="Tvarkytojai").click()
    page.get_by_role("link", name="Pridėti narį").click()
    page.get_by_role("textbox", name="El. paštas *").click()
    page.get_by_role("textbox", name="El. paštas *").fill("koord1@org1.lt")
    page.get_by_role("textbox", name="El. paštas *").press("Tab")
    page.get_by_label("Rolė *").press("Tab")
    page.get_by_role("textbox", name="Telefono numeris").fill("+37060100001")
    page.get_by_role("button", name="Sukurti").click()
    page.get_by_role("link", name="Pridėti narį").click()
    page.get_by_role("textbox", name="El. paštas *").click()
    page.get_by_role("textbox", name="El. paštas *").fill("user2@org1.lt")
    page.get_by_role("textbox", name="El. paštas *").press("Tab")
    page.get_by_label("Rolė *").press("ArrowDown")
    page.get_by_label("Rolė *").select_option("resource_manager")
    page.get_by_label("Rolė *").press("Tab")
    page.get_by_role("textbox", name="El. paštas *").click()
    page.get_by_role("textbox", name="El. paštas *").click()
    page.get_by_role("textbox", name="El. paštas *").press("Home")
    page.get_by_role("textbox", name="El. paštas *").fill("tvark1@org1.lt")
    page.get_by_role("textbox", name="Telefono numeris").click()
    page.get_by_role("textbox", name="Telefono numeris").fill("+37060100002")
    page.get_by_role("button", name="Sukurti").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
