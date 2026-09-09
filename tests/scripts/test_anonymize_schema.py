"""The anonymizer has to find the story text in either schema.

django-cms 5 moved it: djangocms-blog's translation rows became
djangocms-stories content rows. `dataset` resolves a missing table lazily, so
reaching for the wrong name scrubs nothing and says nothing - the dump goes out
with every article's real title and text in it.
"""

import pytest

from scripts.anonymize import STORY_CONTENT_TABLES, _story_content_tables


class FakeDatabase:
    def __init__(self, *tables):
        self.tables = list(tables)


def test_finds_the_stories_table():
    db = FakeDatabase("organization", "djangocms_stories_postcontent")

    assert _story_content_tables(db) == ["djangocms_stories_postcontent"]


def test_finds_the_blog_table_before_the_upgrade():
    db = FakeDatabase("organization", "djangocms_blog_post_translation")

    assert _story_content_tables(db) == ["djangocms_blog_post_translation"]


def test_takes_both_when_an_upgrade_stopped_half_way():
    """Taking only the newer one would send the legacy articles out in full."""
    db = FakeDatabase("organization", "djangocms_stories_postcontent", "djangocms_blog_post_translation")

    assert _story_content_tables(db) == list(STORY_CONTENT_TABLES)


def test_stops_when_the_database_has_neither():
    db = FakeDatabase("organization")

    with pytest.raises(SystemExit) as stop:
        _story_content_tables(db)

    for name in STORY_CONTENT_TABLES:
        assert name in str(stop.value)


def test_every_listed_table_has_a_function_to_anonymize_it():
    """The runner looks the function up by table name, so a typo is a crash."""
    import scripts.anonymize as anonymize

    for table in STORY_CONTENT_TABLES:
        assert hasattr(anonymize, f"_anonymize_{table}")


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
    from unittest.mock import Mock

    from faker import Faker

    from scripts.anonymize import _anonymize_organization

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
    import dataset

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


def test_story_plugin_bodies_are_scrubbed_on_both_schemas(tmp_path):
    """The article body lives in a plugin once the migration moves it there.

    From then on this SQL is the only thing standing between the real text and
    the dump, and it is reached through three joins - exactly the shape that
    breaks quietly when a column is renamed.
    """
    from scripts.anonymize import _scrub_story_plugins

    db = _story_plugin_database(tmp_path / "probe.db")

    _scrub_story_plugins(db)

    bodies = {row["cmsplugin_ptr_id"]: row["body"] for row in db.query("SELECT * FROM djangocms_text_text")}
    assert bodies[1] == "<p>example</p>", "djangocms_stories body survived"
    assert bodies[2] == "<p>example</p>", "djangocms_blog body survived"
    assert bodies[3] == "<p>SLAPTA 3</p>", "a page plugin was scrubbed; only stories are this script's business"


def test_the_plugin_scrub_skips_a_database_without_text_plugins(tmp_path):
    import dataset

    from scripts.anonymize import _scrub_story_plugins

    db = dataset.connect(f"sqlite:///{tmp_path / 'empty.db'}")
    db.query("CREATE TABLE organization (id integer primary key)")

    _scrub_story_plugins(db)
