"""Attach images to stories that already exist.

Expects the stories named in STORY_TITLES and the image folder to be there.
"""


from playwright.sync_api import Page, Playwright, sync_playwright
from utils import IMAGE_FOLDER, SELECT_FILE, browser_page

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Story titles to edit
# These stories have to exist already, and these are the ones create_stories.py
# makes: it counts from one on every run, so "Blog 10" and "Blog 11" - which is
# what this used to name - could never appear without editing that script.
STORY_TITLES = {
    "first": "Blog 1 pavadinimas",
    "fourth": "Blog 2 pavadinimas",
    "second": "Blog 3 pavadinimas",
}

# Images to select
# Both files live in IMAGE_FOLDER - create_blog_posts.py uploads all six there.
# Without the folder the picker looks in the filer root and finds nothing.
IMAGES = {
    "fourth": {"folder": IMAGE_FOLDER, "file": "03.png"},
    "second": {"folder": IMAGE_FOLDER, "file": "05.png"},
}

# UI text constants
UI_TEXT = {
    "save": "Išsaugoti",
    "news": "Naujienos",
    "localhost": "localhost",
    "posts": "Posts...",
}

# -----------------------------------------------------------------------------
# Step functions
# -----------------------------------------------------------------------------

def navigate_to_posts(page: Page) -> None:
    """Navigate to the Posts management page."""
    page.get_by_role("link", name=UI_TEXT["news"]).click()
    page.get_by_role("link", name=UI_TEXT["localhost"]).click()
    page.get_by_role("link", name=UI_TEXT["posts"]).click()


def open_story_edit(page: Page, story_title: str) -> None:
    """Open a story for editing in the CMS sideframe."""
    frame = page.locator("iframe").content_frame
    frame.get_by_role("link", name=story_title).click()


def collapse_fieldset(page: Page) -> None:
    """Collapse the first fieldset in the edit form."""
    frame = page.locator("iframe").content_frame
    frame.locator("#fieldsetcollapser1").click()


def close_sideframe(page: Page) -> None:
    """Close the CMS sideframe."""
    page.locator(".cms-sideframe-close").first.click()


def select_image_in_popup(page: Page, folder: str | None, filename: str) -> None:
    """Select an image file in the file browser popup."""
    if folder:
        page.get_by_role("link", name=folder).click()
    page.get_by_role("link", name=filename).click()


def add_image_to_story(page: Page, folder: str | None, filename: str) -> None:
    """Open file browser popup and select an image for the story."""
    frame = page.locator("iframe").content_frame

    with page.expect_popup() as popup_info:
        frame.get_by_role("link", name=SELECT_FILE).click()

    popup = popup_info.value
    select_image_in_popup(popup, folder, filename)
    popup.close()


def save_story(page: Page) -> None:
    """Save the story form."""
    frame = page.locator("iframe").content_frame
    frame.get_by_role("button", name=UI_TEXT["save"], exact=True).click()


# -----------------------------------------------------------------------------
# Workflow functions
# -----------------------------------------------------------------------------

def edit_first_story(page: Page) -> None:
    """Edit the story configured as "first" - collapse the fieldset and close."""
    print(f"Editing story: {STORY_TITLES['first']}...")
    open_story_edit(page, STORY_TITLES["first"])
    collapse_fieldset(page)
    close_sideframe(page)
    print(f"✅ {STORY_TITLES['first']} edited successfully.")


def add_image_to_fourth_story(page: Page) -> None:
    """Add an image to the story configured as "fourth", from the Skaiciai folder."""
    print(f"Adding image to story: {STORY_TITLES['fourth']}...")
    open_story_edit(page, STORY_TITLES["fourth"])
    collapse_fieldset(page)
    add_image_to_story(page, IMAGES["fourth"]["folder"], IMAGES["fourth"]["file"])
    save_story(page)
    print(f"✅ Image added to {STORY_TITLES['fourth']} successfully.")


def add_image_to_second_story(page: Page) -> None:
    """Add an image to the story configured as "second"."""
    print(f"Adding image to story: {STORY_TITLES['second']}...")
    open_story_edit(page, STORY_TITLES["second"])
    collapse_fieldset(page)
    add_image_to_story(page, IMAGES["second"].get("folder"), IMAGES["second"]["file"])
    save_story(page)
    print(f"✅ Image added to {STORY_TITLES['second']} successfully.")


def run_stories_image_workflow(page: Page) -> None:
    """Run the complete workflow for managing story images."""
    print("\nStarting stories image workflow...\n")

    navigate_to_posts(page)
    edit_first_story(page)

    navigate_to_posts(page)
    add_image_to_fourth_story(page)

    navigate_to_posts(page)
    add_image_to_second_story(page)

    close_sideframe(page)
    page.get_by_role("link", name=UI_TEXT["news"]).click()

    print("\n🎉 Stories image workflow completed successfully!")


# -----------------------------------------------------------------------------
# Main runner
# -----------------------------------------------------------------------------

def run(playwright: Playwright) -> None:
    with browser_page(playwright) as page:
        run_stories_image_workflow(page)


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
