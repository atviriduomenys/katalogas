from playwright.sync_api import Page, Playwright, sync_playwright

from utils import BASE_URL, login

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BLOG_DATA = {
    "title": "Blog 1 pavadinimas",
    "abstract": "Blog 1 santrauka",
    "content": "Blog 1 ilgas, pilnas straipsnio tekstas\n\naaa\n\nbbb\n\nccc",
}


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def go_to_blog_list(page: Page) -> None:
    """Navigate to the blog list page."""
    page.get_by_role("link", name="Naujienos").click()
    page.get_by_role("link", name="Tiklaraštis").click()
    page.wait_for_load_state("networkidle")


def start_new_blog_post(page: Page) -> None:
    """Start creating a new blog post."""
    page.get_by_role("link", name="New +").click()
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
    page.get_by_role("link", name="Publish").click()
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
        frame.get_by_role("link", name="Pasirinkti bylą").click()
    page1 = page1_info.value

    with page1.expect_popup() as page2_info:
        page1.get_by_role("link", name="Naujas aplankas").click()
    page2 = page2_info.value
    page2.get_by_role("textbox", name="Vardas:").fill("Skaiciai")
    page2.get_by_role("button", name="Išsaugoti").click()
    page2.close()

    page1.goto(f"{BASE_URL}/admin/filer/folder/?_pick=file&_popup=1")
    page1.get_by_role("link", name="Skaiciai").click()
    folder_url = page1.url
    page1.get_by_role("link", name="įkelti bylas").set_input_files(
        ["02.jpg", "05.png", "04.png", "03.png", "01.jpg", "00.jpg"]
    )
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
    browser = playwright.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    page.goto(BASE_URL)
    login(page)
    go_to_blog_list(page)
    create_blog_post(page, BLOG_DATA)
    open_post_properties(page)
    upload_images_to_blog(page)
    view_blog_post(page)

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
