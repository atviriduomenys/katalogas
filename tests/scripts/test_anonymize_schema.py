"""The anonymizer has to find the story text in either schema.

django-cms 5 moved it: djangocms-blog's translation rows became
djangocms-stories content rows. `dataset` resolves a missing table lazily, so
reaching for the wrong name scrubs nothing and says nothing - the dump goes out
with every article's real title and text in it.
"""

import pytest

from scripts.anonymize import STORY_CONTENT_TABLE, _story_content_table


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


def test_every_listed_table_has_a_function_to_anonymize_it():
    """The runner looks the function up by table name, so a typo is a crash."""
    import scripts.anonymize as anonymize

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
