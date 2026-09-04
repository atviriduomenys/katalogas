"""Add one story with an image, through the cms toolbar.

Expects the image folder to exist already - create_blog_posts.py makes it.
"""

import re

from playwright.sync_api import Playwright, sync_playwright
from utils import IMAGE_FOLDER, SELECT_FILE, browser_page


def run(playwright: Playwright) -> None:
    with browser_page(playwright) as page:
        page.get_by_role("link", name="Blog").click()
        page.get_by_role("link", name="Sukurti").click()
        page.locator("iframe").content_frame.get_by_text(re.compile(r"(Naujas|New) Article")).click()
        page.get_by_role("link", name="Kitas").click()
        page.locator("iframe").content_frame.get_by_role("textbox", name="Pavadinimas", exact=True).click()
        page.locator("iframe").content_frame.get_by_role("textbox", name="Pavadinimas", exact=True).fill("Blog 5 pavadinimas")
        page.locator("iframe").content_frame.get_by_role("textbox", name="Pavadinimas", exact=True).press("Tab")
        page.locator("iframe").content_frame.get_by_role("textbox", name="Nuoroda").press("Tab")
        page.locator("iframe").content_frame.locator("#id_1-abstract_editor").get_by_role("textbox").click()
        page.locator("iframe").content_frame.locator("#id_1-abstract_editor").get_by_role("textbox").fill("Format\nStyles\n\nBlog 5 santrauka")
        page.locator("iframe").content_frame.get_by_role("textbox", name="Subtitle").click()
        page.locator("iframe").content_frame.get_by_role("textbox", name="Subtitle").fill("Blog 5 subtitle")
        page.locator("iframe").content_frame.get_by_role("paragraph").filter(has_text=re.compile(r"^$")).click()
        page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("textbox").filter(has_text="Format StylesSmallKbdVarSamp").fill("Format\nStyles\n\nBlog 5 pagrindinis tekstas\n\nPradžia....")
        page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("textbox").filter(has_text="Format StylesSmallKbdVarSamp").press("Shift+Home")
        page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Bold").click()
        page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Italic").click()
        page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Underline").click()
        page.locator("iframe").content_frame.locator("#id_1-post_text_editor").get_by_role("button", name="Italic").click()
        page.get_by_role("link", name="Sukurti").nth(1).click()
        page.get_by_role("link", name=re.compile(r"Publikuoti Article dabar|Publish Article now")).click()
        page.get_by_role("link", name="Blog").click()
        page.get_by_role("link", name="Tinklaraštis").click()
        page.get_by_role("link", name="Straipsnių sąrašas...").click()
        page.locator("iframe").content_frame.get_by_role("link", name="Blog 5 pavadinimas").click()
        page.locator("iframe").content_frame.locator("#fieldsetcollapser1").click()
        with page.expect_popup() as page1_info:
            page.locator("iframe").content_frame.get_by_role("link", name=SELECT_FILE).click()
        page1 = page1_info.value
        page1.get_by_role("link", name=IMAGE_FOLDER).click()
        page1.get_by_role("link", name="03.png").click()
        page1.close()
        page.get_by_role("link", name="Išsaugoti", exact=True).click()
        page.get_by_role("link", name="Žiūrėti publikuotą").click()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
