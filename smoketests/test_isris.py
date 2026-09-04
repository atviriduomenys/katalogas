from __future__ import annotations

import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from taggit.models import Tag

from vitrina.datasets.models import (
    Contact,
    ContactKind,
    DCATResourceSubclass,
    Dataset,
    Version,
)
from vitrina.orgs.models import Organization, Representative
from vitrina.structure.models import Metadata
from vitrina.uapi import AgentType, Environment
from vitrina.uapi.models import Agent, AgentEnvironment
from vitrina.users.models import User

from .conftest import add_tag, submit_form, today_suffix

PASSWORD = "test"

USERS = {
    "admin": "admin@example.com",
    "supervisor": "supervisor@example.com",
    "coordinator": "vssa.coordinator@example.com",
    "manager": "vssa.manager@example.com",
}

VSSA_REG_CODE = "188772433"
VSSA_TITLE = "Valstybės skaitmeninių sprendimų agentūra"
AGENT_TITLE = "ISRIS Agent"

# Full codenames (as stored in Metadata.name / Dataset.name property).
CODENAMES = {
    ("isris", "is"): "datasets/gov/vssa/isris",
    ("isris", "service"): "datasets/gov/vssa/isris/uapi",
    ("isris", "dataset"): "datasets/gov/vssa/isris/uapi/is",
    ("dvms", "is"): "datasets/gov/vssa/dvms",
    ("dvms", "service"): "datasets/gov/vssa/dvms/uapi",
    ("dvms", "dataset"): "datasets/gov/vssa/dvms/uapi/is",
    ("dcat", "is"): "datasets/gov/vssa/dcat",
    ("dcat", "service"): "datasets/gov/vssa/dcat/uapi",
    ("dcat", "dataset"): "datasets/gov/vssa/dcat/uapi/is",
}

# Relative machine names entered into the `name` form field (parent prefix is
# added by the application when building the full codename).
RELATIVE = {"is": "isris", "service": "uapi", "dataset": "is"}

TITLES = {
    ("isris", "service"): "ISRIS duomenų paslauga",
    ("isris", "dataset"): "ISRIS duomenys",
    ("dvms", "service"): "DVMS duomenų paslauga",
    ("dvms", "dataset"): "DVMS duomenys",
    ("dcat", "service"): "DCAT duomenų paslauga",
    ("dcat", "dataset"): "DCAT duomenys",
}


def code(key):
    return CODENAMES[key]


def _get_or_create_user(email, **kwargs):
    user, created = User.objects.get_or_create(email=email, defaults=kwargs)
    changed = created
    if not user.check_password(PASSWORD):
        user.set_password(PASSWORD)
        changed = True
    for key, value in kwargs.items():
        if getattr(user, key, None) != value:
            setattr(user, key, value)
            changed = True
    if user.status != User.ACTIVE or user.failed_login_attempts:
        user.status = User.ACTIVE
        user.failed_login_attempts = 0
        user.password_last_updated = timezone.now()
        changed = True
    if changed:
        user.save()
    return user


def dataset_pk(codename):
    meta = Metadata.objects.filter(name=codename).first()
    return meta.dataset_id if meta else None


@pytest.fixture(scope="module")
def seed():
    """Idempotently create the prerequisite objects in the live database."""
    org, _ = Organization.objects.get_or_create(
        company_code=VSSA_REG_CODE,
        defaults={"title": VSSA_TITLE, "name": "vssa", "kind": Organization.GOV, "slug": "vssa"},
    )
    # The form validates the dataset `name` (full codename) against the
    # organization's `name` as a prefix. The seeded information systems use the
    # "datasets/gov/vssa/..." codename convention, so align the org name with it.
    if org.name != "datasets/gov/vssa":
        org.name = "datasets/gov/vssa"
        org.save()

    admin = _get_or_create_user(USERS["admin"], is_superuser=True, is_staff=True, is_active=True)
    supervisor = _get_or_create_user(USERS["supervisor"], is_staff=True, is_active=True)
    coordinator = _get_or_create_user(USERS["coordinator"], is_active=True)
    manager = _get_or_create_user(USERS["manager"], is_active=True)

    Representative.objects.get_or_create(
        user=supervisor,
        organization=org,
        defaults={"role": Representative.SUPERVISOR, "content_object": org, "email": USERS["supervisor"]},
    )
    Representative.objects.get_or_create(
        user=coordinator,
        organization=org,
        defaults={
            "role": Representative.RESOURCE_COORDINATOR,
            "content_object": org,
            "email": USERS["coordinator"],
        },
    )
    Representative.objects.get_or_create(
        user=manager,
        organization=org,
        defaults={"role": Representative.RESOURCE_MANAGER, "content_object": org, "email": USERS["manager"]},
    )

    agent, _ = Agent.objects.get_or_create(
        title=AGENT_TITLE, organization=org, defaults={"object_type": AgentType.SPINTA}
    )

    org_ct = ContentType.objects.get_for_model(Organization)
    contact, _ = Contact.objects.get_or_create(
        organization=org,
        content_type=org_ct,
        object_id=org.pk,
        defaults={"kind": ContactKind.ORG, "email": "info@vssa.test"},
    )

    # The dataset form's `tags` field is an autocomplete-only tag widget, so a
    # pre-existing tag must exist for the test to attach one.
    Tag.objects.get_or_create(name="isris")

    AgentEnvironment.objects.get_or_create(
        agent=agent,
        environment=Environment.TESTING,
        defaults={
            "auth_server_url": "https://am.test-apigw.gov.lt",
            "api_gate_server_url": "https://test-apigw.gov.lt",
            "agent_address": "127.0.0.1",
            "is_enabled": True,
        },
    )

    subclass_by_name = {s.name: s for s in DCATResourceSubclass.objects.all()}
    is_subclass = subclass_by_name["information_system"]
    service_subclass = subclass_by_name["service"]
    dataset_subclass = subclass_by_name["dataset"]

    dataset_ct = ContentType.objects.get_for_model(Dataset)

    def ensure_is(codename):
        if Metadata.objects.filter(name=codename, dataset__organization=org).exists():
            return Dataset.objects.get(metadata__name=codename).pk
        ds = Dataset(
            subclass=is_subclass,
            organization=org,
            access_rights=Dataset.CONFIDENTIAL,
            slug=codename,
        )
        ds.set_current_language("lt")
        ds.title = codename.rsplit("/", 1)[-1]
        ds.description = codename
        ds.save()
        mv = Version.objects.create(dataset=ds, version=1, status="draft")
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            name=codename,
            type="dataset",
            content_type=dataset_ct,
            object_id=ds.pk,
            dataset=ds,
            title=ds.title,
            description=ds.description,
            version=1,
            metadata_version=mv,
            draft=True,
        )
        return ds.pk

    is_pks = {
        key: ensure_is(code(("isris", "is")) if key == "isris" else code((key, "is")))
        for key in ("isris", "dvms", "dcat")
    }

    return {
        "org": org,
        "org_id": org.pk,
        "admin": admin,
        "manager": manager,
        "agent": agent,
        "agent_id": agent.pk,
        "contact_id": contact.pk,
        "is_pks": is_pks,
        "subclass": {
            "information_system": is_subclass.uuid,
            "service": service_subclass.uuid,
            "dataset": dataset_subclass.uuid,
        },
    }


# --------------------------------------------------------------------------- #
# User registration / auth smoke                                              #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_login_all_roles(page, login_user, seed):
    for email in USERS.values():
        login_user(page, email)
        assert "/login/" not in page.url, f"Login failed for {email}"
        page.goto("/")


@pytest.mark.django_db
def test_coordinator_registration_pages_load(page, seed):
    page.goto("/partner/register-info/")
    assert page.url.endswith("/partner/register-info/")

    page.goto("/fake-viisp/complete-login/")
    assert page.url.endswith("/fake-viisp/complete-login/")


# --------------------------------------------------------------------------- #
# Agent registration                                                          #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_agent_registration(page, login_user, seed):
    login_user(page, USERS["manager"])

    if not Agent.objects.filter(title=AGENT_TITLE).exists():
        page.goto(f"/organizations/{seed['org_id']}/agents/add/")
        page.fill('input[name="title"]', AGENT_TITLE)
        submit_form(page)
        assert Agent.objects.filter(title=AGENT_TITLE).exists()

    agent = Agent.objects.get(title=AGENT_TITLE)
    if not AgentEnvironment.objects.filter(agent=agent).exists():
        page.goto(f"/organizations/{seed['org_id']}/agents/{agent.pk}/environments/add/")
        page.select_option('select[name="environment"]', label="Testavimo")
        page.fill('input[name="agent_address"]', "127.0.0.1")
        page.fill('input[name="auth_server_url"]', "https://am.test-apigw.gov.lt")
        page.fill('input[name="api_gate_server_url"]', "https://test-apigw.gov.lt")
        submit_form(page)
        assert AgentEnvironment.objects.filter(agent=agent).exists()


# --------------------------------------------------------------------------- #
# Resource registration (inline forms)                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_resource_registration_inline(page, login_user, seed):
    login_user(page, USERS["manager"])

    if not dataset_pk(code(("isris", "service"))):
        is_pk = seed["is_pks"]["isris"]
        page.goto(f"/orgs/{seed['org_id']}/datasets/{is_pk}/child-resources/add/")
        page.check(f'input[value="{seed["subclass"]["service"]}"]')
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

        page.fill('input[name="name"]', code(("isris", "service")))
        page.fill('input[name="title"]', TITLES[("isris", "service")])
        page.fill('textarea[name="description"], input[name="description"]', "ISRIS UAPI paslauga")
        page.fill('input[name="endpoint_url"]', "https://api.isris.test/uapi")
        page.fill(
            'textarea[name="endpoint_description"], input[name="endpoint_description"]',
            "https://api.isris.test/spec.json",
        )
        add_tag(page, "tags", "isris")
        page.select_option('select[name="contact"]', value=str(seed["contact_id"]))
        page.select_option('select[name="access_rights"]', label="Vieši")
        submit_form(page)
        assert dataset_pk(code(("isris", "service"))), "Inline service not created"

    if not dataset_pk(code(("isris", "dataset"))):
        service_pk = dataset_pk(code(("isris", "service")))
        page.goto(f"/orgs/{seed['org_id']}/datasets/{service_pk}/child-resources/add/")
        page.check(f'input[value="{seed["subclass"]["dataset"]}"]')
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

        page.fill('input[name="name"]', code(("isris", "dataset")))
        page.fill('input[name="title"]', TITLES[("isris", "dataset")])
        page.fill('textarea[name="description"], input[name="description"]', "ISRIS duomenys")
        add_tag(page, "tags", "isris")
        page.select_option('select[name="contact"]', value=str(seed["contact_id"]))
        page.select_option('select[name="access_rights"]', label="Vieši")
        submit_form(page)
        assert dataset_pk(code(("isris", "dataset"))), "Inline dataset not created"


# --------------------------------------------------------------------------- #
# Resource registration (wizard / DCAT forms)                                 #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_resource_registration_wizard(page, login_user, seed):
    login_user(page, USERS["manager"])

    for key in ("dvms", "dcat"):
        if dataset_pk(code((key, "service"))):
            continue
        is_pk = seed["is_pks"][key]
        page.goto(f"/organization/{seed['org_id']}/dcat/dataset/parent/{is_pk}/subclass/{seed['subclass']['service']}/")
        page.wait_for_selector("#wizard-fragment-form")
        page.fill('input[name="name"]', RELATIVE["service"])
        page.fill('input[name="title"]', TITLES[(key, "service")])
        page.fill('textarea[name="description"], input[name="description"]', f"{key} UAPI paslauga")
        page.fill('input[name="endpoint_url"]', f"https://api.{key}.test/uapi")
        page.fill(
            'textarea[name="endpoint_description"], input[name="endpoint_description"]',
            f"https://api.{key}.test/spec.json",
        )
        add_tag(page, "tags", "isris")
        page.select_option('select[name="contact"]', value=str(seed["contact_id"]))
        page.select_option('select[name="access_rights"]', label="Vieši")
        page.evaluate(
            "(oid) => { const s = document.querySelector('select[name=organization]'); if (s) { const o = document.createElement('option'); o.value = String(oid); o.textContent = 'x'; s.appendChild(o); s.value = String(oid); } }",
            seed["org_id"],
        )
        page.evaluate("() => document.querySelector('#wizard-fragment-form').requestSubmit()")
        page.wait_for_load_state("networkidle")
        assert dataset_pk(code((key, "service"))), f"Wizard service {key} not created"

    for key in ("dvms", "dcat"):
        if dataset_pk(code((key, "dataset"))):
            continue
        service_pk = dataset_pk(code((key, "service")))
        page.goto(
            f"/organization/{seed['org_id']}/dcat/dataset/parent/{service_pk}/subclass/{seed['subclass']['dataset']}/"
        )
        page.wait_for_selector("#wizard-fragment-form")
        page.fill('input[name="name"]', RELATIVE["dataset"])
        page.fill('input[name="title"]', TITLES[(key, "dataset")])
        page.fill('textarea[name="description"], input[name="description"]', f"{key} duomenys")
        add_tag(page, "tags", "isris")
        page.select_option('select[name="contact"]', value=str(seed["contact_id"]))
        page.select_option('select[name="access_rights"]', label="Vieši")
        page.evaluate(
            "(oid) => { const s = document.querySelector('select[name=organization]'); if (s) { const o = document.createElement('option'); o.value = String(oid); o.textContent = 'x'; s.appendChild(o); s.value = String(oid); } }",
            seed["org_id"],
        )
        page.evaluate("() => document.querySelector('#wizard-fragment-form').requestSubmit()")
        page.wait_for_load_state("networkidle")
        assert dataset_pk(code((key, "dataset"))), f"Wizard dataset {key} not created"


# --------------------------------------------------------------------------- #
# Resource discovery                                                          #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_resource_discovery_isris(page, login_user, seed):
    login_user(page, USERS["manager"])
    service_pk = dataset_pk(code(("isris", "service")))
    assert service_pk, "ISRIS service must exist"

    page.goto(f"/orgs/{seed['org_id']}/datasets/")
    page.click(f'a[href="/datasets/{service_pk}/"]')
    page.wait_for_load_state("networkidle")

    page.goto(f"/datasets/{service_pk}/update/")
    page.wait_for_selector("#dataset-form")
    new_title = f"{TITLES[('isris', 'service')]} {today_suffix()}"
    page.fill('input[name="title"]', new_title)
    submit_form(page)

    page.goto(f"/datasets/{service_pk}/")
    assert new_title in page.content()


@pytest.mark.django_db
def test_resource_discovery_dcat(page, login_user, seed):
    login_user(page, USERS["manager"])
    service_pk = dataset_pk(code(("dvms", "service")))
    assert service_pk, "DVMS service must exist"

    page.goto(f"/orgs/{seed['org_id']}/datasets/")
    page.click(f'a[href="/datasets/{service_pk}/"]')
    page.wait_for_load_state("networkidle")

    page.goto(f"/datasets/{service_pk}/update/")
    page.wait_for_selector("#dataset-form")
    new_title = f"{TITLES[('dvms', 'service')]} {today_suffix()}"
    page.fill('input[name="title"]', new_title)
    submit_form(page)

    page.goto(f"/datasets/{service_pk}/")
    assert new_title in page.content()


# --------------------------------------------------------------------------- #
# Admin                                                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_admin_isris(page, login_user, seed):
    login_user(page, USERS["admin"])
    service_pk = dataset_pk(code(("isris", "service")))
    assert service_pk, "ISRIS service must exist"

    page.goto("/admin/vitrina_datasets/dataset/")
    page.fill('input[name="q"]', TITLES[("isris", "service")])
    page.click('input[type="submit"][value="Ieškoti"]')
    page.wait_for_load_state("networkidle")
    page.click(f'a[href*="/admin/vitrina_datasets/dataset/{service_pk}/change/"]')
    page.wait_for_load_state("networkidle")
    assert f"/admin/vitrina_datasets/dataset/{service_pk}/change/" in page.url


@pytest.mark.django_db
def test_admin_dcat(page, login_user, seed):
    login_user(page, USERS["admin"])
    service_pk = dataset_pk(code(("dcat", "service")))
    assert service_pk, "DCAT service (datasets/gov/vssa/dcat/uapi) must exist"

    page.goto("/admin/vitrina_datasets/dataset/")
    page.fill('input[name="q"]', TITLES[("dcat", "service")])
    page.click('input[type="submit"][value="Ieškoti"]')
    page.wait_for_load_state("networkidle")
    page.click(f'a[href*="/admin/vitrina_datasets/dataset/{service_pk}/change/"]')
    page.wait_for_load_state("networkidle")
    assert f"/admin/vitrina_datasets/dataset/{service_pk}/change/" in page.url
