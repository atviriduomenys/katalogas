from playwright.sync_api import Page, Playwright, sync_playwright
import itertools
from utils import BASE_URL, login

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Number of stories to create
STORY_COUNT = 3
STORIES_START_INDEX = 5
_story_counter = itertools.count(start=STORIES_START_INDEX)


def generate_story_data() -> dict:
    """Generate story data dynamically based on index."""
    index = next(_story_counter)
    return {
        "title": f"Blog {index} pavadinimas",
        "abstract": f"Blog {index} santrauka - Tai yra trumpas aprašymas apie ką kalbama šioje naujienoje.",
        "content": f"Blog {index} pilnas straipsnio tekstas\nTai yra pagrindinis turinio tekstas.",
        "extra_content": f"Papildomas Blog {index} tekstas.",
    }


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def go_to_stories_list(page: Page) -> None:
    """Navigate to the stories list page."""
    page.get_by_role("link", name="Naujienos").click()
    page.wait_for_load_state("networkidle")


def start_new_story(page: Page) -> None:
    """Start creating a new story."""
    page.get_by_role("link", name="Sukurti").click()
    frame = page.locator("iframe").content_frame
    frame.get_by_text("Naujas +").click()
    page.get_by_role("link", name="Kitas", exact=True).click()


def _fill_basic_fields(frame, story: dict) -> None:
    """Fill title, abstract, and initial content fields."""
    frame.get_by_role("textbox", name="Pavadinimas").fill(story["title"])
    frame.locator("#id_1-abstract_editor").get_by_role("textbox").fill(story["abstract"])
    frame.locator("#id_1-post_text_editor").get_by_role("textbox").fill(story["content"])


def fill_story_form(page: Page, story: dict) -> None:
    """Fill in the story form with formatting."""
    frame = page.locator("iframe").content_frame
    _fill_basic_fields(frame, story)


def submit_story_form(page: Page) -> None:
    """Submit the story creation form."""
    page.get_by_role("link", name="Sukurti").nth(1).click()
    page.wait_for_load_state("networkidle")


def publish_story(page: Page) -> None:
    """Publish the created story."""
    page.get_by_role("link", name="Publish").click()
    page.wait_for_load_state("networkidle")


def create_story(page: Page, story: dict) -> None:
    """Run the full story creation flow."""
    print(f"Creating story: {story['title']}...")
    start_new_story(page)
    fill_story_form(page, story)
    submit_story_form(page)
    publish_story(page)
    print(f"✅ {story['title']} created and published successfully.")


def create_multiple_stories(page: Page, count: int) -> None:
    """Create multiple stories with dynamically generated data."""
    print(f"\nStarting to create {count} stories...\n")

    for i in range(STORY_COUNT):
        story_data = generate_story_data()
        create_story(page, story_data)
        print()

    print(f"🎉 Successfully created and published {count} stories!")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    page.goto(BASE_URL)
    login(page)
    go_to_stories_list(page)
    create_multiple_stories(page, STORY_COUNT)

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
