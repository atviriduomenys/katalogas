"""The anonymizer has to find the story text, and stop when it cannot.

`dataset` would silently scrub a missing table; pre-upgrade and half-upgraded dumps are refused.
"""

from unittest.mock import Mock

import dataset
import pytest
from faker import Faker

from scripts import anonymize
from scripts.anonymize import (
    LEGACY_STORY_TABLE,
    STORY_CONTENT_TABLE,
    _anonymize_adp_cms_page,
    _anonymize_cms_pagecontent,
    _anonymize_organization,
    _scrub_story_plugins,
    _story_content_table,
)


class FakeDatabase:
    def __init__(self, *tables):
        self.tables = list(tables)


def test_finds_the_stories_table():
    db = FakeDatabase("organization", "djangocms_stories_postcontent")

    assert _story_content_table(db) == STORY_CONTENT_TABLE


def test_stops_on_a_database_without_it():
    """A pre-upgrade dump lands here now, and refusing is the right answer."""
    db = FakeDatabase("organization", "djangocms_blog_post_translation")

    with pytest.raises(SystemExit) as stop:
        _story_content_table(db)

    assert STORY_CONTENT_TABLE in str(stop.value)


def test_stops_on_a_database_an_upgrade_left_half_done():
    """Both tables standing: scrubbing only the stories one would ship the legacy text."""
    db = FakeDatabase("organization", STORY_CONTENT_TABLE, LEGACY_STORY_TABLE)

    with pytest.raises(SystemExit) as stop:
        _story_content_table(db)

    assert LEGACY_STORY_TABLE in str(stop.value)


def test_page_content_keeps_no_editor_names():
    """cms 5 repeats created_by and changed_by on page content, not just on the page."""
    contents = FakeTable([{"id": 1, "created_by": "vardas.pavarde", "changed_by": "kitas.redaktorius"}])

    _anonymize_cms_pagecontent({"cms_pagecontent": contents}, Faker(), Mock(), {})

    written = contents.updates[0]
    assert set(written) == {"id", "created_by", "changed_by"}
    assert "vardas.pavarde" not in " ".join(str(v) for v in written.values())


def test_every_listed_table_has_a_function_to_anonymize_it():
    """The runner looks the function up by table name, so a typo is a crash."""
    assert hasattr(anonymize, f"_anonymize_{STORY_CONTENT_TABLE}")


class FakeTable:
    """Enough of `dataset`'s Table to see what a scrub writes."""

    def __init__(self, rows):
        self.rows = rows
        self.updates = []

    def all(self):
        return list(self.rows)

    def update(self, data, keys):
        self.updates.append(data)


def test_organizations_lose_every_field_people_type_contacts_into():
    """website is free text, and a production copy had a real address in it."""
    table = FakeTable([{"id": 1, "email": "tikras@istaiga.lt", "website": "kontaktai@istaiga.lt"}])
    db = {"organization": table}
    fake = Faker()
    fake.seed_instance(0)

    _anonymize_organization(db, fake, Mock(), {})

    written = table.updates[0]
    assert set(written) == {"id", "email", "phone", "address", "website"}
    assert "istaiga.lt" not in " ".join(str(v) for v in written.values())


def _story_plugin_database(path):
    """The four tables the plugin scrub joins, with one row of each kind."""
    db = dataset.connect(f"sqlite:///{path}")
    db.query("CREATE TABLE django_content_type (id integer primary key, app_label text, model text)")
    db.query("CREATE TABLE cms_placeholder (id integer primary key, content_type_id integer)")
    db.query("CREATE TABLE cms_cmsplugin (id integer primary key, placeholder_id integer)")
    db.query("CREATE TABLE djangocms_text_text (cmsplugin_ptr_id integer primary key, body text)")

    types = [(1, "djangocms_stories", "postcontent"), (2, "djangocms_blog", "post"), (3, "cms", "page")]
    for pk, app_label, model in types:
        db.query(f"INSERT INTO django_content_type VALUES ({pk}, '{app_label}', '{model}')")
    for pk in (1, 2, 3):
        db.query(f"INSERT INTO cms_placeholder VALUES ({pk}, {pk})")
        db.query(f"INSERT INTO cms_cmsplugin VALUES ({pk}, {pk})")
        db.query(f"INSERT INTO djangocms_text_text VALUES ({pk}, '<p>SLAPTA {pk}</p>')")
    return db


def test_story_plugin_bodies_are_scrubbed(tmp_path):
    """Placeholder-mode configs keep article text in text plugins, reached through three joins."""
    db = _story_plugin_database(tmp_path / "probe.db")

    _scrub_story_plugins(db)

    bodies = {row["cmsplugin_ptr_id"]: row["body"] for row in db.query("SELECT * FROM djangocms_text_text")}
    assert bodies[1] == "<p>example</p>", "djangocms_stories body survived"
    assert bodies[3] == "<p>SLAPTA 3</p>", "a page plugin was scrubbed; only stories are this script's business"


def test_the_plugin_scrub_skips_a_database_without_text_plugins(tmp_path):
    db = dataset.connect(f"sqlite:///{tmp_path / 'empty.db'}")
    db.query("CREATE TABLE organization (id integer primary key)")

    _scrub_story_plugins(db)


def test_old_portal_pages_are_scrubbed_in_their_own_table():
    """_anonymize_adp_cms_page scrubs adp_cms_page, and leaves news_item alone."""
    pages = FakeTable([{"id": 1, "title": "Tikras puslapis", "body": "<p>Tikras</p>"}])
    news = FakeTable([{"id": 7, "title": "Naujiena"}])

    _anonymize_adp_cms_page({"adp_cms_page": pages, "news_item": news}, Faker(), Mock(), {})

    assert [row["id"] for row in pages.updates] == [1]
    assert news.updates == []
