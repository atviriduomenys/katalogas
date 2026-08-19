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
    page.get_by_role("textbox", name="Slaptažodis *").fill("Liabas.12345")
    page.get_by_role("textbox", name="Slaptažodis *").press("Enter")
    page.get_by_role("button", name="Prisijungti").click()
    page.get_by_role("link", name="Blog").click()
    page.get_by_role("link", name="Sukurti").click()
    page.locator("iframe").content_frame.get_by_text("Naujas Article").click()
    page.get_by_role("link", name="Kitas").click()
    page.locator("iframe").content_frame.get_by_role("textbox", name="Pavadinimas", exact=True).click()
    page.locator("iframe").content_frame.get_by_role("textbox", name="Pavadinimas", exact=True).fill("Blog 3 pavadinimas")
    page.locator("iframe").content_frame.get_by_role("textbox", name="Pavadinimas", exact=True).press("Tab")
    page.locator("iframe").content_frame.get_by_role("textbox", name="Nuoroda").press("Tab")
    page.locator("iframe").content_frame.locator("#id_1-abstract_editor").get_by_role("textbox").click()
    page.locator("iframe").content_frame.locator("#id_1-abstract_editor").get_by_role("textbox").fill("Format\nStyles\n\nBlog 3 santrauka")
    page.locator("iframe").content_frame.get_by_role("textbox", name="Subtitle").click()
    page.locator("iframe").content_frame.get_by_role("textbox", name="Subtitle").fill("Blog 3 subtitle")
    page.locator("iframe").content_frame.get_by_role("paragraph").filter(has_text=re.compile(r"^$")).click()
    page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("textbox").filter(has_text="Format StylesSmallKbdVarSamp").fill("Format\nStyles\n\nBlog 3 pagrindinis tekstas\n\nPradžia....")
    page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("textbox").filter(has_text="Format StylesSmallKbdVarSamp").press("Shift+Home")
    page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Bold").click()
    page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Italic").click()
    page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Italic").click()
    page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Underline").click()
    page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Italic").click()
    page.get_by_role("link", name="Sukurti").nth(1).click()
    page.get_by_role("link", name="Publikuoti Article dabar").click()
    page.get_by_role("link", name="Blog").click()
    page.get_by_role("link", name="Tinklaraštis").click()
    page.get_by_role("link", name="Straipsnių sąrašas...").click()
    page.locator("iframe").content_frame.get_by_role("link", name="Blog 3 pavadinimas").click()
    page.locator("iframe").content_frame.locator("#fieldsetcollapser1").click()
    with page.expect_popup() as page1_info:
        page.locator("iframe").content_frame.get_by_role("link", name=" Pasirinkti bylą").click()
    page1 = page1_info.value
    page1.get_by_role("link", name="skaičiai").click()
    page1.get_by_role("link", name="03.png").click()
    page1.close()
    page.get_by_role("link", name="Išsaugoti", exact=True).click()
    page.get_by_role("link", name="Žiūrėti publikuotą").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
