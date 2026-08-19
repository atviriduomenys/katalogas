from playwright.sync_api import Page, Playwright, sync_playwright

from utils import BASE_URL, login

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Story titles to edit
STORY_TITLES = {
    "first": "Blog 11 pavadinimas",
    "fourth": "Blog 10 pavadinimas",
    "second": "Blog 3 pavadinimas",
}

# Images to select
IMAGES = {
    "fourth": {"folder": "Skaiciai", "file": "03.png"},
    "second": {"file": "05.png"},
}

# UI text constants
UI_TEXT = {
    "select_file": " Pasirinkti bylą",
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
        frame.get_by_role("link", name=UI_TEXT["select_file"]).click()

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
    """Edit the first story (Blogas 1) - just collapse fieldset and close."""
    print(f"Editing story: {STORY_TITLES['first']}...")
    open_story_edit(page, STORY_TITLES["first"])
    collapse_fieldset(page)
    close_sideframe(page)
    print(f"✅ {STORY_TITLES['first']} edited successfully.")


def add_image_to_fourth_story(page: Page) -> None:
    """Add image to the fourth story (Blog 4) from the Skaiciai folder."""
    print(f"Adding image to story: {STORY_TITLES['fourth']}...")
    open_story_edit(page, STORY_TITLES["fourth"])
    collapse_fieldset(page)
    add_image_to_story(page, IMAGES["fourth"]["folder"], IMAGES["fourth"]["file"])
    save_story(page)
    print(f"✅ Image added to {STORY_TITLES['fourth']} successfully.")


def add_image_to_second_story(page: Page) -> None:
    """Add image to the second story (Blog 2)."""
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
    browser = playwright.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    page.goto(BASE_URL)
    login(page)
    run_stories_image_workflow(page)

    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
