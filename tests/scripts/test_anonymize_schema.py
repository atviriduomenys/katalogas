"""The anonymizer has to find the story text in either schema.

django-cms 5 moved it: djangocms-blog's translation rows became
djangocms-stories content rows. `dataset` resolves a missing table lazily, so
reaching for the wrong name scrubs nothing and says nothing - the dump goes out
with every article's real title and text in it.
"""

import pytest

from scripts.anonymize import STORY_CONTENT_TABLES, _story_content_table


class FakeDatabase:
    def __init__(self, *tables):
        self.tables = list(tables)


def test_prefers_the_stories_table():
    db = FakeDatabase("organization", "djangocms_stories_postcontent")

    assert _story_content_table(db) == "djangocms_stories_postcontent"


def test_falls_back_to_the_blog_table_before_the_upgrade():
    db = FakeDatabase("organization", "djangocms_blog_post_translation")

    assert _story_content_table(db) == "djangocms_blog_post_translation"


def test_stops_when_the_database_has_neither():
    db = FakeDatabase("organization")

    with pytest.raises(SystemExit) as stop:
        _story_content_table(db)

    for name in STORY_CONTENT_TABLES:
        assert name in str(stop.value)


def test_every_listed_table_has_a_function_to_anonymize_it():
    """The runner looks the function up by table name, so a typo is a crash."""
    import scripts.anonymize as anonymize

    for table in STORY_CONTENT_TABLES:
        assert hasattr(anonymize, f"_anonymize_{table}")
