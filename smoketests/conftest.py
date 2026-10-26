from __future__ import annotations

import datetime
import re
import shutil

import pytest

# Admin credentials provided by the target instance (docker-compose.yml sets
# DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD).
ADMIN_EMAIL = "test@test.com"
ADMIN_PASSWORD = "test"

DEFAULT_BASE_URL = "http://localhost:8000"


def pytest_configure(config):
    # Smoke tests run against a live instance; default to the local
    # docker-compose app when --base-url is not given explicitly.
    if not config.getvalue("--base-url"):
        config.option.base_url = DEFAULT_BASE_URL


def today_suffix() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def login(page, email: str, password: str) -> bool:
    """Log a user in through the custom /login/ form; True on success."""
    page.goto("/login/")
    page.fill('input[name="username"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"], input[type="submit"]')
    page.wait_for_load_state("networkidle")
    return "/login/" not in page.url


@pytest.fixture
def login_user():
    return login


@pytest.fixture(scope="session")
def admin_page(browser, base_url):
    """A dedicated browser context logged in as the instance administrator."""
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    if not login(page, ADMIN_EMAIL, ADMIN_PASSWORD):
        pytest.fail(
            f"Could not log in as admin ({ADMIN_EMAIL}). The target instance must provide "
            "this superuser account (docker-compose sets DJANGO_SUPERUSER_EMAIL / "
            "DJANGO_SUPERUSER_PASSWORD).",
            pytrace=False,
        )
    yield page
    context.close()


def register_user(page, email: str, password: str) -> bool:
    """Register a new account through /register/; True when registration
    succeeds (the account then awaits e-mail confirmation)."""
    page.goto("/register/")
    page.fill('input[name="first_name"]', "Vssa")
    page.fill('input[name="last_name"]', "Testuotojas")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password1"]', password)
    page.fill('input[name="password2"]', password)
    page.check('input[name="agree_to_terms"]')
    try:
        page.locator('iframe[src*="recaptcha/api2/anchor"]').first.wait_for(state="visible", timeout=5000)
        page.frame_locator('iframe[src*="recaptcha/api2/anchor"]').first.locator(
            ".recaptcha-checkbox-border, #recaptcha-anchor"
        ).first.click(timeout=5000)
        page.wait_for_timeout(1000)
    except Exception:
        # The test reCAPTCHA keys accept any response value, so the hidden
        # field can be filled directly when the widget cannot be clicked.
        page.evaluate(
            "() => { const el = document.getElementById('g-recaptcha-response'); if (el) el.value = 'smoke-test'; }"
        )
    page.evaluate("() => { const b = document.getElementById('submit-id-submit'); if (b) b.disabled = false; }")
    page.click("#submit-id-submit")
    page.wait_for_load_state("networkidle")
    return "/register/" not in page.url


def _sent_mail_content(admin_page, email: str, subject_part: str) -> str:
    """Open the newest mail to `email` whose subject contains `subject_part`
    in the SentMail admin and return its content."""
    admin_page.goto("/admin/vitrina_messages/sentmail/")
    admin_page.fill('input[name="q"]', email)
    admin_page.click('input[type="submit"]')
    admin_page.wait_for_load_state("networkidle")
    rows = admin_page.locator(f'#result_list tbody tr:has-text("{email}")')
    for i in range(rows.count()):
        row = rows.nth(i)
        if subject_part in row.inner_text():
            row.locator("a").first.click()
            admin_page.wait_for_load_state("networkidle")
            return admin_page.locator('textarea[name="email_content"]').input_value()
    raise AssertionError(f"No sent mail to {email!r} with subject containing {subject_part!r}")


def confirm_registration(page, admin_page, email: str) -> None:
    """Confirm a freshly registered account via the mail found in SentMail."""
    content = _sent_mail_content(admin_page, email, "Prašome patvirtinti")
    match = re.search(r"https?://[^\s\"'<>)]+/register/account-confirm-email/[-:\w]+/?", content)
    assert match, f"Confirmation link not found in the registration mail to {email!r}"
    # Confirm from an anonymous context: allauth logs out any authenticated
    # user whose session opens a confirmation link belonging to a different
    # account, which would otherwise invalidate the admin session.
    context = admin_page.context.browser.new_context()
    anon = context.new_page()
    try:
        anon.goto(match.group(0))
        anon.locator("#confirm_email_form button[type=submit], #confirm_email_form input[type=submit]").click()
        anon.wait_for_load_state("networkidle")
    finally:
        context.close()


def reset_password(page, admin_page, email: str, password: str) -> None:
    """Reset a user's password via the /reset/ flow and SentMail."""
    page.goto("/reset/")
    origin = re.match(r"(https?://[^/]+)", page.url).group(1)
    page.fill('input[name="email"]', email)
    page.click('button[type="submit"], input[type="submit"]')
    page.wait_for_load_state("networkidle")
    content = _sent_mail_content(admin_page, email, "Slaptažodžio atstatymas")
    match = re.search(r"https?://[^\s\"'<>)]+/reset/[-\w]+/[-\w]+/?", content)
    assert match, f"Password reset link not found in the mail to {email!r}"
    # The mail is rendered with the configured site domain (e.g. "localhost"
    # without a port); point the link at the instance under test instead.
    page.goto(re.sub(r"^(https?://[^/]+)", origin, match.group(0)))
    page.fill('input[name="new_password1"]', password)
    page.fill('input[name="new_password2"]', password)
    page.click('button[type="submit"], input[type="submit"]')
    page.wait_for_load_state("networkidle")


def ensure_user(page, admin_page, email: str, password: str) -> None:
    """Make sure the user can log in with the given password: log in, or
    register (and confirm via SentMail), or reset the password."""
    if login(page, email, password):
        return
    if register_user(page, email, password):
        confirm_registration(page, admin_page, email)
        if login(page, email, password):
            return
    reset_password(page, admin_page, email, password)
    assert login(page, email, password), f"Could not ensure user {email!r} can log in"


def select2(page, field_name: str, value: str, timeout: int = 8000) -> None:
    """Pick an option in a django-select2 widget (AJAX or JS-only)."""
    container = page.locator(f'select[name="{field_name}"] ~ .select2-container')
    container.locator(".select2-selection").first.click()
    # For multiple widgets the search field lives inside the selection; for
    # single widgets select2 appends the dropdown (with the search field) to
    # the body.
    search = container.locator(".select2-search__field")
    if not search.count():
        search = page.locator(".select2-dropdown .select2-search__field")
    search.first.fill(value)
    option = page.locator(f'.select2-results__option:not(.select2-results__message):has-text("{value}")').first
    option.wait_for(state="visible", timeout=timeout)
    option.click()
    if container.locator(".select2-search__field").count():
        page.keyboard.press("Escape")


def add_tag(page, field_name: str, value: str) -> None:
    """Attach a tag to a tagulous widget: accept an autocomplete suggestion
    when one exists, otherwise commit the typed text with Enter (Tagulous
    creates the tag on save)."""
    sel = (
        f'input[name="{field_name}"] ~ .select2-container .select2-selection, '
        f'select[name="{field_name}"] ~ .select2-container .select2-selection'
    )
    if page.locator(sel).count():
        container = page.locator(
            f'select[name="{field_name}"] ~ .select2-container, input[name="{field_name}"] ~ .select2-container'
        ).first
        container.locator(".select2-selection").click()
        search = container.locator(".select2-search__field")
        if not search.count():
            search = page.locator(".select2-dropdown .select2-search__field")
        search.first.fill(value)
        page.wait_for_timeout(500)
        option = page.locator(f'.select2-results__option:not(.select2-results__message):has-text("{value}")').first
        if option.count():
            option.click()
        else:
            search.first.press("Enter")
        page.keyboard.press("Escape")
    else:
        field = page.locator(f'input[name="{field_name}"]').first
        field.fill(value)
        field.press("Enter")
        page.wait_for_timeout(200)


def submit_form(page) -> None:
    page.click('#dataset-form button[type="submit"], form#dataset-form input[type="submit"]')
    page.wait_for_load_state("networkidle")


@pytest.fixture(scope="session")
def browser_type_launch_args(pytestconfig):
    chromium = shutil.which("chromium") or shutil.which("chromium-browser")
    args = {"executable_path": chromium, "headless": True}
    if pytestconfig.getoption("--headed", default=False):
        args["headless"] = False
    return args
