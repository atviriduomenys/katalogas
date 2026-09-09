"""Web-only smoke tests for the ISRIS scenario.

These tests drive a running Katalogas instance exclusively through the
browser — no direct database access is used. The target instance must
provide the admin account (see `conftest.ADMIN_EMAIL`); every other user
is registered through the UI on first run, so the tests are idempotent
and work against a remote instance.
"""

from __future__ import annotations

import re


from .conftest import add_tag, ensure_user, select2, submit_form, today_suffix

PASSWORD = "Kat-Smoke-2026!aZ9"

COORDINATOR_EMAIL = "vssa.coordinator@example.com"
MANAGER_EMAIL = "vssa.manager@example.com"

VSSA_TITLE = "Valstybės skaitmeninių sprendimų agentūra"
VSSA_REG_CODE = "188772433"

IS_TITLES = {
    "isris": "ISRIS informacinė sistema",
    "dvms": "DVMS informacinė sistema",
    "dcat": "DCAT informacinė sistema",
}
SERVICE_TITLES = {
    "isris": "ISRIS duomenų paslauga",
    "dvms": "DVMS duomenų paslauga",
    "dcat": "DCAT duomenų paslauga",
}
DATASET_TITLES = {
    "isris": "ISRIS duomenys",
    "dvms": "DVMS duomenys",
    "dcat": "DCAT duomenys",
}

AGENT_TITLE = "ISRIS Agent"
TAG = "isris"
CONTACT_NAME = "VSSA kontaktinis asmuo"
CONTACT_EMAIL = "info@vssa.test"
PHONE = "+37060000000"


# --------------------------------------------------------------------------- #
# UI navigation helpers (no ORM — pks are resolved through the browser)       #
# --------------------------------------------------------------------------- #


def find_org_pk(page) -> int | None:
    """Resolve the VSSA organization pk via the organizations list, or None."""
    page.goto("/organizations/")
    links = page.locator(f'a[href^="/orgs/"]:has-text("{VSSA_TITLE}")')
    if not links.count():
        # Fall back to scanning list pages (the free-text search may not find
        # organizations whose raw title column is not populated).
        for page_no in range(2, 11):
            page.goto(f"/organizations/?page={page_no}")
            if not page.locator('a[href^="/orgs/"]').count():
                break
            links = page.locator(f'a[href^="/orgs/"]:has-text("{VSSA_TITLE}")')
            if links.count():
                break
    if not links.count():
        return None
    return int(re.search(r"/orgs/(\d+)/", links.first.get_attribute("href")).group(1))


def create_org_via_admin(admin_page) -> None:
    """Create the VSSA organization through the admin UI (the suite assumes
    only the admin account exists on the target instance)."""
    admin_page.goto("/admin/vitrina_orgs/organization/add/")
    admin_page.fill('textarea[name="title"], input[name="title"]', VSSA_TITLE)
    admin_page.fill('input[name="slug"]', "vssa")
    admin_page.fill('textarea[name="name"], input[name="name"]', "datasets/gov/vssa/")
    admin_page.fill('input[name="company_code"]', VSSA_REG_CODE)
    admin_page.select_option("select[name='is_public']", value="true")
    if admin_page.locator("select[name='_position']").count():
        position = admin_page.locator("select[name='_position']")
        if position.locator("option[value='sorted-child']").count():
            position.select_option(value="sorted-child")
        else:
            position.select_option(value="first-child")
    admin_page.locator("input[name='_save']").click()
    admin_page.wait_for_load_state("networkidle")


def ensure_org(page, admin_page) -> int:
    org_pk = find_org_pk(page)
    if org_pk is None:
        create_org_via_admin(admin_page)
        org_pk = find_org_pk(page)
        assert org_pk, f"Organization {VSSA_TITLE!r} could not be created via the admin"
    # The organization must be publicly visible, otherwise its pages (and the
    # dataset lists) are not accessible even to its coordinators.
    page.goto(f"/orgs/{org_pk}/")
    if "Prieiga uždrausta" in page.content():
        admin_page.goto(f"/admin/vitrina_orgs/organization/{org_pk}/change/")
        admin_page.select_option("select[name='is_public']", value="true")
        admin_page.locator("input[name='_save']").click()
        admin_page.wait_for_load_state("networkidle")
        page.goto(f"/orgs/{org_pk}/")
        assert "Prieiga uždrausta" not in page.content(), "Organization is not publicly visible"
    return org_pk


def find_dataset_pk(page, org_pk: int, title: str) -> int | None:
    """Find a dataset of the organization by its title, or None."""
    page.goto(f"/orgs/{org_pk}/datasets/")
    page.fill("#search-input", title)
    page.press("#search-input", "Enter")
    page.wait_for_load_state("networkidle")
    links = page.locator(f'a.dataset-list-title:has-text("{title}")')
    if not links.count():
        page.goto(f"/orgs/{org_pk}/datasets/")
        links = page.locator(f'a.dataset-list-title:has-text("{title}")')
    if not links.count():
        return None
    match = re.search(r"/datasets/(\d+)/", links.first.get_attribute("href"))
    return int(match.group(1)) if match else None


def select_subclass(page, label: str) -> None:
    page.locator(f'label.box:has-text("{label}")').first.click()


def create_resource(page) -> int:
    """Submit #dataset-form and return the pk of the created resource."""
    page.locator('#dataset-form button[type="submit"]').click()
    try:
        page.wait_for_url(re.compile(r"/datasets/\d+/(?:\?.*)?$"), timeout=15000)
    except Exception:
        errors = page.locator(".errorlist, .invalid-feedback, .invalid-feedback ul li").all_inner_texts()
        raise AssertionError(f"Resource creation failed ({page.url}): {errors}")
    return int(re.search(r"/datasets/(\d+)/", page.url).group(1))


def select_org(page, field_name: str, org_pk: int) -> None:
    """Pick the VSSA organization in a select2 widget; fall back to
    injecting the option when the widget or its AJAX lookup misbehaves."""
    try:
        select2(page, field_name, VSSA_TITLE)
        return
    except Exception:
        pass
    page.evaluate(
        """([name, oid]) => {
            const select = document.querySelector(`select[name="${name}"]`);
            if (select) {
                const option = document.createElement('option');
                option.value = String(oid);
                option.selected = true;
                select.appendChild(option);
                select.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""",
        [field_name, org_pk],
    )


def ensure_is_root(page, org_pk: int, title: str) -> int:
    """Make sure an information system with the given title exists."""
    existing = find_dataset_pk(page, org_pk, title)
    if existing:
        return existing
    page.goto(f"/orgs/{org_pk}/datasets/add/")
    select_subclass(page, "Informacinė sistema")
    submit_form(page)
    page.fill('input[name="title"]', title)
    page.fill('textarea[name="description"]', f"{title} aprašymas")
    select_org(page, "creator", org_pk)
    page.select_option('select[name="information_system_type"]', index=1)
    page.select_option('select[name="information_system_importance"]', index=1)
    select_org(page, "information_system_publishers", org_pk)
    page.select_option('select[name="access_rights"]', label="Vieši")
    return create_resource(page)


def ensure_contact(page, org_pk: int) -> None:
    """Make sure the organization has a contact (required by the inline
    service form)."""
    page.goto(f"/orgs/{org_pk}/contacts/")
    if page.get_by_text(CONTACT_NAME).count() or page.get_by_text(CONTACT_EMAIL).count():
        return
    page.goto(f"/orgs/{org_pk}/contacts/add/")
    page.fill('input[name="contact_name"]', CONTACT_NAME)
    page.fill('input[name="email"]', CONTACT_EMAIL)
    page.fill('input[name="phone"]', PHONE)
    page.fill('input[name="position"]', "VSSA testuotojas")
    page.locator("#contact-form #submit-id-submit").click()
    page.wait_for_load_state("networkidle")
    assert page.get_by_text(CONTACT_NAME).count(), "Contact was not created"


def ensure_child_service(page, org_pk: int, parent_pk: int, title: str) -> int:
    """Make sure a child service of the given parent exists (inline form)."""
    existing = find_dataset_pk(page, org_pk, title)
    if existing:
        return existing
    page.goto(f"/orgs/{org_pk}/datasets/{parent_pk}/child-resources/add/")
    select_subclass(page, "Duomenų paslauga")
    submit_form(page)
    page.fill('input[name="title"]', title)
    page.fill('textarea[name="description"]', f"{title} aprašymas")
    page.fill('input[name="endpoint_url"]', "https://api.isris.test/uapi")
    page.locator('input[name="endpoint_description"]').first.fill("https://api.isris.test/spec.json")
    add_tag(page, "tags", TAG)
    page.select_option('select[name="access_rights"]', label="Vieši")
    page.select_option('select[name="contact"]', index=1)
    return create_resource(page)


def ensure_child_dataset(page, org_pk: int, parent_pk: int, title: str) -> int:
    """Make sure a child dataset of the given parent exists (inline form)."""
    existing = find_dataset_pk(page, org_pk, title)
    if existing:
        return existing
    page.goto(f"/orgs/{org_pk}/datasets/{parent_pk}/child-resources/add/")
    select_subclass(page, "Duomenų rinkinys")
    submit_form(page)
    page.fill('input[name="title"]', title)
    page.fill('textarea[name="description"]', f"{title} aprašymas")
    add_tag(page, "tags", TAG)
    page.select_option('select[name="access_rights"]', label="Vieši")
    return create_resource(page)


def create_wizard_resource(
    page, org_pk: int, parent_key: str, picker_label: str, name: str, title: str, *, service: bool
) -> None:
    """Create a resource through the wizard shell UI (full page with htmx/Alpine).

    The wizard create form is an htmx fragment meant to be loaded into the
    wizard shell (`/orgs/<pk>/wizard/`). Opening the fragment URL directly
    renders a bare page without the shell's CSS/JS — without htmx the form
    would be submitted natively and the select2/tagulous widgets would race
    their initialization, which makes the flow flaky.
    """
    page.goto(f"/orgs/{org_pk}/wizard/")
    # The org form is auto-loaded over htmx; once it is in, htmx and Alpine
    # are up (and x-cloak'ed tree nodes can be expanded).
    page.wait_for_selector("#wizard-main-pane #wizard-fragment-form")
    # Expand the whole tree so the target row is visible regardless of depth.
    page.locator(".wizard-tree-expand-toggle").click()
    row = page.locator(f'.wizard-tree-node[data-node-key="{parent_key}"] > .wizard-tree-row')
    row.wait_for(state="visible")
    row.locator(".wizard-tree-add").click()
    page.locator(".wizard-picker-card:not(.is-disabled)").filter(
        has=page.locator(".wizard-picker-card-title", has_text=picker_label)
    ).first.click()
    # attemptCreate shows the pane again (with the stale parent/org form)
    # before the htmx GET swaps in the create fragment; both forms contain a
    # name input, so wait for the form whose hx-post points at a create URL.
    page.wait_for_selector('#wizard-main-pane form[hx-post*="/subclass/"] input[name="name"]')
    # Widget media arrives with the fragment and select2/tagulous initialise
    # asynchronously — wait for the containers before filling those fields.
    page.wait_for_selector('#wizard-main-pane input[name="tags"] ~ .select2-container .select2-selection')
    page.wait_for_selector('#wizard-main-pane select[name="organization"] ~ .select2-container .select2-selection')
    page.fill('#wizard-fragment-form input[name="name"]', name)
    page.fill('#wizard-fragment-form input[name="title"]', title)
    page.fill('#wizard-fragment-form textarea[name="description"]', f"{title} aprašymas")
    if service:
        page.fill('#wizard-fragment-form input[name="endpoint_url"]', f"https://api.{name}.test/uapi")
    add_tag(page, "tags", TAG)
    select_org(page, "organization", org_pk)
    page.locator("#wizard-save-btn").click()
    page.wait_for_selector(
        "#wizard-main-pane .notification.is-success, #wizard-main-pane .notification.is-danger"
    )
    errors = page.locator("#wizard-main-pane .notification.is-danger").all_inner_texts()
    assert not errors, f"Wizard creation of {title!r} failed: {errors}"
    # The success swap keeps the form marked dirty for a short grace period;
    # wait it out so the next navigation is not blocked by the beforeunload
    # guard (Playwright dismisses the dialog, which cancels the navigation).
    page.wait_for_function("() => window.wizardFormDirty === false")


def member_listed(page, org_pk: int, email: str) -> bool:
    page.goto(f"/orgs/{org_pk}/members/")
    return page.locator(f'table tr:has-text("{email}")').count() > 0


# --------------------------------------------------------------------------- #
# User registration / auth smoke                                              #
# --------------------------------------------------------------------------- #


def test_register_and_login_all_roles(page, admin_page):
    """The admin account must exist on the target instance (the admin_page
    fixture logs it in once per session); other users are registered on
    first run and then simply log in."""
    ensure_user(page, admin_page, COORDINATOR_EMAIL, PASSWORD)
    assert "/login/" not in page.url
    ensure_user(page, admin_page, MANAGER_EMAIL, PASSWORD)
    assert "/login/" not in page.url


def test_coordinator_role_approval(page, admin_page):
    """The coordinator registers as a data provider (fake VIISP login) and
    the admin approves the request, granting the open data coordinator role."""
    ensure_user(page, admin_page, COORDINATOR_EMAIL, PASSWORD)
    org_pk = ensure_org(page, admin_page)
    if member_listed(page, org_pk, COORDINATOR_EMAIL):
        return

    page.goto("/logout/")
    page.goto("/login/")
    # The fake VIISP login is only linked from the login page (and only
    # available on DEBUG instances); resolve its URL from there.
    link = page.locator("#fake-viisp-complete-login")
    if link.count():
        page.goto(link.get_attribute("href"))
    else:
        page.goto("/accounts/fake-viisp/complete-login/")
    page.fill('input[name="username"]', COORDINATOR_EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.fill('input[name="lt_company_code"]', VSSA_REG_CODE)
    page.locator("#submit-id-submit").click()
    page.wait_for_load_state("networkidle")

    page.goto("/partner/register-info/")
    page.locator("#partner-register").click()
    page.wait_for_load_state("networkidle")
    select_org(page, "organization", org_pk)
    page.fill('input[name="coordinator_phone_number"]', PHONE)
    page.set_input_files(
        'input[name="request_form"]',
        {"name": "request.txt", "mimeType": "text/plain", "buffer": b"ISRIS smoke test request"},
    )
    page.locator("#submit-id-submit").click()
    page.wait_for_load_state("networkidle")
    assert any(
        part in page.url
        for part in (
            "/partner/register-complete/",
            "/partner/representative/exists/",
            "/partner/representative-request/exists/",
        )
    ), f"Unexpected partner registration outcome: {page.url}"

    admin_page.goto("/coordinator-admin/vitrina_orgs/representativerequest/")
    rows = admin_page.locator(f'tr:has-text("{COORDINATOR_EMAIL}")')
    assert rows.count(), f"No representative request found for {COORDINATOR_EMAIL}"
    approve = rows.first.locator('a:has-text("Patvirtinti")')
    assert approve.count(), "The representative request is not awaiting approval"
    approve.first.click()
    admin_page.wait_for_load_state("networkidle")
    admin_page.locator("#confirm-form input[type=submit], #confirm-form button[type=submit]").click()
    admin_page.wait_for_load_state("networkidle")
    assert member_listed(page, org_pk, COORDINATOR_EMAIL), "Coordinator is not listed as an organization member"


def test_resource_coordinator_role(page, admin_page):
    """The admin grants the resource coordinator role to the manager."""
    ensure_user(page, admin_page, MANAGER_EMAIL, PASSWORD)
    org_pk = ensure_org(page, admin_page)
    if member_listed(page, org_pk, MANAGER_EMAIL):
        return

    admin_page.goto(f"/orgs/{org_pk}/members/add/")
    admin_page.fill('input[name="email"]', MANAGER_EMAIL)
    admin_page.select_option('select[name="role"]', label="Duomenų išteklių koordinatorius")
    admin_page.locator("#submit-id-submit").click()
    admin_page.wait_for_load_state("networkidle")
    assert member_listed(page, org_pk, MANAGER_EMAIL), "Manager is not listed as an organization member"


# --------------------------------------------------------------------------- #
# Resource registration (inline forms)                                        #
# --------------------------------------------------------------------------- #


def test_resource_registration_inline(page, admin_page):
    ensure_user(page, admin_page, MANAGER_EMAIL, PASSWORD)
    org_pk = ensure_org(page, admin_page)
    ensure_contact(page, org_pk)

    is_pk = ensure_is_root(page, org_pk, IS_TITLES["isris"])
    service_pk = ensure_child_service(page, org_pk, is_pk, SERVICE_TITLES["isris"])
    ensure_child_dataset(page, org_pk, service_pk, DATASET_TITLES["isris"])

    assert find_dataset_pk(page, org_pk, IS_TITLES["isris"]), "Inline information system not found"
    assert find_dataset_pk(page, org_pk, SERVICE_TITLES["isris"]), "Inline service not created"
    assert find_dataset_pk(page, org_pk, DATASET_TITLES["isris"]), "Inline dataset not created"


# --------------------------------------------------------------------------- #
# Resource registration (wizard / DCAT forms)                                 #
# --------------------------------------------------------------------------- #


def test_resource_registration_wizard(page, admin_page):
    ensure_user(page, admin_page, MANAGER_EMAIL, PASSWORD)
    org_pk = ensure_org(page, admin_page)

    for key in ("dvms", "dcat"):
        parent_pk = ensure_is_root(page, org_pk, IS_TITLES[key])
        if find_dataset_pk(page, org_pk, SERVICE_TITLES[key]) is None:
            create_wizard_resource(
                page, org_pk, f"is:{parent_pk}", "Duomenų paslauga", "uapi", SERVICE_TITLES[key], service=True
            )
        assert find_dataset_pk(page, org_pk, SERVICE_TITLES[key]), f"Wizard service for {key} not created"
        service_pk = find_dataset_pk(page, org_pk, SERVICE_TITLES[key])
        if find_dataset_pk(page, org_pk, DATASET_TITLES[key]) is None:
            create_wizard_resource(
                page, org_pk, f"service:{service_pk}", "Duomenų rinkinys", "is", DATASET_TITLES[key], service=False
            )
        assert find_dataset_pk(page, org_pk, DATASET_TITLES[key]), f"Wizard dataset for {key} not created"


# --------------------------------------------------------------------------- #
# Agent registration                                                          #
# --------------------------------------------------------------------------- #


def test_agent_registration(page, admin_page):
    ensure_user(page, admin_page, MANAGER_EMAIL, PASSWORD)
    org_pk = ensure_org(page, admin_page)

    page.goto(f"/orgs/{org_pk}/")
    page.locator('a:has-text("Agentai")').first.click()
    page.wait_for_load_state("networkidle")

    agent_link = page.locator(f'table tr:has-text("{AGENT_TITLE}") a')
    if agent_link.count():
        agent_link.first.click()
    else:
        page.locator('a:has-text("Pridėti agentą")').first.click()
        page.wait_for_load_state("networkidle")
        page.fill('input[name="title"]', AGENT_TITLE)
        page.select_option('select[name="object_type"]', label="Spinta")
        page.locator("#submit-id-submit").click()
        page.wait_for_load_state("networkidle")
    agent_url = page.url

    if not page.get_by_text("Testavimo").count() and page.locator('a:has-text("Pridėti aplinką")').count():
        page.locator('a:has-text("Pridėti aplinką")').first.click()
        page.wait_for_load_state("networkidle")
        page.select_option('select[name="environment"]', label="Testavimo")
        page.fill('input[name="agent_address"]', "127.0.0.1")
        page.fill('input[name="auth_server_url"]', "https://am.test-apigw.gov.lt")
        page.fill('input[name="api_gate_server_url"]', "https://test-apigw.gov.lt")
        page.locator("#submit-id-submit").click()
        page.wait_for_load_state("networkidle")
        if "Nepavyko pasiekti autorizacijos serverio" in page.content():
            # Creating an environment registers it with the authorization
            # server, which may be unreachable on a minimal instance.
            return
        page.goto(agent_url)
    assert page.get_by_text("Testavimo").count(), "Agent environment was not created"


# --------------------------------------------------------------------------- #
# Resource discovery                                                          #
# --------------------------------------------------------------------------- #


def _resource_discovery(page, admin_page, title: str) -> None:
    ensure_user(page, admin_page, MANAGER_EMAIL, PASSWORD)
    org_pk = ensure_org(page, admin_page)
    dataset_pk = find_dataset_pk(page, org_pk, title)
    assert dataset_pk, f"{title!r} must exist (created by earlier tests)"

    page.goto(f"/datasets/{dataset_pk}/")
    page.locator("#change_dataset").click()
    page.wait_for_selector("#dataset-form")
    new_title = f"{title} {today_suffix()}"
    page.fill('input[name="title"]', new_title)
    # Resources created through the wizard have no contact, but the inline
    # update form requires one.
    contact = page.locator('select[name="contact"]')
    if contact.count() and not contact.first.input_value():
        contact.first.select_option(index=1)
    submit_form(page)
    assert f"/datasets/{dataset_pk}/update/" not in page.url, (
        f"Resource update failed: {page.locator('.is-danger, .invalid-feedback').all_inner_texts()}"
    )

    page.goto(f"/datasets/{dataset_pk}/")
    assert new_title in page.content()


def test_resource_discovery_isris(page, admin_page):
    _resource_discovery(page, admin_page, SERVICE_TITLES["isris"])


def test_resource_discovery_dcat(page, admin_page):
    _resource_discovery(page, admin_page, SERVICE_TITLES["dcat"])


# --------------------------------------------------------------------------- #
# Admin                                                                       #
# --------------------------------------------------------------------------- #


def _admin_dataset_check(admin_page, title: str) -> None:
    admin_page.goto("/admin/vitrina_datasets/dataset/")
    admin_page.fill('input[name="q"]', title)
    admin_page.press('input[name="q"]', "Enter")
    admin_page.wait_for_load_state("networkidle")
    links = admin_page.locator(f'#result_list tbody a:has-text("{title}")')
    assert links.count(), f"Dataset {title!r} not found in the admin search"
    links.first.click()
    admin_page.wait_for_load_state("networkidle")
    assert "/change/" in admin_page.url


def test_admin_isris(admin_page):
    _admin_dataset_check(admin_page, SERVICE_TITLES["isris"])


def test_admin_dcat(admin_page):
    _admin_dataset_check(admin_page, SERVICE_TITLES["dcat"])
