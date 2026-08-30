"""Create stories, and the filer folder with the images they use.

Uploads the local images named in IMAGES; see the README for where they come from.
"""

import os
import re
from pathlib import Path

from playwright.sync_api import Page, Playwright, sync_playwright
from utils import BASE_URL, IMAGE_FOLDER, SELECT_FILE, browser_page

IMAGES = ["00.jpg", "01.jpg", "02.jpg", "03.png", "04.png", "05.png"]


def _image_paths() -> list[str]:
    """Where the uploaded images come from.

    The files are not in the repository. Point VITRINA_UI_IMAGES at a directory
    holding them, or run the script from one - and say so plainly rather than
    letting the upload fail on an empty selection.
    """
    directory = Path(os.environ.get("VITRINA_UI_IMAGES", "."))
    missing = [name for name in IMAGES if not (directory / name).is_file()]
    if missing:
        raise SystemExit(
            f"Missing image files in {directory.resolve()}: {', '.join(missing)}.\n"
            f"Set VITRINA_UI_IMAGES to the directory that holds {', '.join(IMAGES)}."
        )
    return [str(directory / name) for name in IMAGES]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Numbered past what create_stories.py makes (Blog 1..3). Sharing a title with
# one of those leaves two links with the same name, and a locator that matches
# both fails on Playwright's strict mode.
BLOG_DATA = {
    "title": "Blog 4 pavadinimas",
    "abstract": "Blog 4 santrauka",
    "content": "Blog 4 ilgas, pilnas straipsnio tekstas\n\naaa\n\nbbb\n\nccc",
}


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def go_to_blog_list(page: Page) -> None:
    """Navigate to the blog list page."""
    page.get_by_role("link", name="Naujienos").click()
    page.get_by_role("link", name="Tinklaraštis").click()
    page.wait_for_load_state("networkidle")


def start_new_blog_post(page: Page) -> None:
    """Start creating a new blog post."""
    page.get_by_role("link", name=re.compile(r"(Naujas|New) \+")).click()
    page.get_by_role("link", name="Kitas").click()
    page.wait_for_load_state("networkidle")


def fill_blog_form(page: Page, blog: dict) -> None:
    """Fill in the blog post form fields."""
    frame = page.locator("iframe").content_frame
    frame.get_by_role("textbox", name="Pavadinimas").fill(blog["title"])
    frame.locator("#id_1-abstract_editor").get_by_role("textbox").fill(blog["abstract"])
    frame.locator("#id_1-post_text_editor").get_by_role("textbox").fill(blog["content"])
    page.wait_for_load_state("networkidle")


def submit_blog_form(page: Page) -> None:
    """Submit the blog post creation form."""
    page.get_by_role("link", name="Sukurti").click()
    page.wait_for_load_state("networkidle")


def publish_blog_post(page: Page) -> None:
    """Publish the created blog post."""
    page.get_by_role("link", name=re.compile(r"Publish|Publikuoti")).click()
    page.wait_for_load_state("networkidle")


def create_blog_post(page: Page, blog: dict) -> None:
    """Run the full blog post creation flow."""
    print(f"Creating blog post: {blog['title']}...")
    start_new_blog_post(page)
    fill_blog_form(page, blog)
    submit_blog_form(page)
    publish_blog_post(page)
    print(f"✅ {blog['title']} created and published successfully.")


def open_post_properties(page: Page) -> None:
    """Open the blog post properties panel."""
    page.get_by_role("link", name="+ properties...").click()
    frame = page.locator("iframe").content_frame
    frame.locator("#fieldsetcollapser1").click()


def upload_images_to_blog(page: Page) -> None:
    """Upload images to the blog post media library."""
    with page.expect_popup() as page1_info:
        frame = page.locator("iframe").content_frame
        frame.get_by_role("link", name=SELECT_FILE).click()
    page1 = page1_info.value

    with page1.expect_popup() as page2_info:
        page1.get_by_role("link", name="Naujas aplankas").click()
    page2 = page2_info.value
    page2.get_by_role("textbox", name="Vardas:").fill(IMAGE_FOLDER)
    page2.get_by_role("button", name="Išsaugoti").click()
    page2.close()

    page1.goto(f"{BASE_URL}/admin/filer/folder/?_pick=file&_popup=1")
    page1.get_by_role("link", name=IMAGE_FOLDER).click()
    folder_url = page1.url
    # set_input_files wants an input element (or a label pointing at one), and this
    # is a link, so go through the chooser the click opens.
    with page1.expect_file_chooser() as chooser:
        page1.get_by_role("link", name="įkelti bylas").click()
    chooser.value.set_files(_image_paths())
    # Back to the same folder, newest first - its id differs between databases.
    page1.goto(f"{folder_url}&order_by=-modified_at")
    page1.get_by_role("link", name="01.jpg").click()
    page1.close()

    page.get_by_role("link", name="Išsaugoti", exact=True).click()
    page.wait_for_load_state("networkidle")


def view_blog_post(page: Page) -> None:
    """Navigate to view the published blog post."""
    page.get_by_label("breadcrumbs").get_by_role("link", name="Naujienos").click()
    page.get_by_role("link", name="skaityti daugiau »").click()
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(playwright: Playwright) -> None:
    with browser_page(playwright) as page:
        go_to_blog_list(page)
        create_blog_post(page, BLOG_DATA)
        open_post_properties(page)
        upload_images_to_blog(page)
        view_blog_post(page)


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
