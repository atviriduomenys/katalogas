"""--keep-public-content spares only what the site shows, and never the byline."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import dataset
import pytest
from faker import Faker

from scripts import anonymize
from scripts.anonymize import (
    STORY_CONTENT_TABLE,
    _anonymize_adp_cms_page,
    _anonymize_djangocms_stories_postcontent,
    _anonymize_news_item,
)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
BYLINE = "<p>Autorius: Jonas Jonaitis</p>"


@pytest.fixture
def keep_public_content(monkeypatch):
    monkeypatch.setattr(anonymize, "_KEEP_PUBLIC_CONTENT", True)


def _stories_database(path, posts):
    """posts: (title, version state, date_published, date_published_end) for each story."""
    db = dataset.connect(f"sqlite:///{path}")
    db["django_content_type"].insert_many(
        [
            {"id": 1, "app_label": "djangocms_stories", "model": "postcontent"},
            {"id": 2, "app_label": "cms", "model": "pagecontent"},
        ]
    )
    post_table = db.create_table("djangocms_stories_post")
    post_table.create_column("date_published", db.types.datetime)
    post_table.create_column("date_published_end", db.types.datetime)
    for pk, (title, state, start, end) in enumerate(posts, start=1):
        db["djangocms_stories_post"].insert({"id": pk, "date_published": start, "date_published_end": end})
        db[STORY_CONTENT_TABLE].insert(
            {
                "id": pk,
                "post_id": pk,
                "language": "lt",
                "title": title,
                "slug": title.lower(),
                "subtitle": "",
                "abstract": f"{BYLINE}<p>SANTRAUKA</p>",
                "meta_description": "",
                "meta_title": "",
                "meta_keywords": "",
                "post_text": f"{BYLINE}<p>TEKSTAS</p>",
            }
        )
        db["djangocms_versioning_version"].insert({"id": pk, "object_id": pk, "content_type_id": 1, "state": state})
    # A published page version with the same object id must not make a story look published.
    db["djangocms_versioning_version"].insert({"id": 100, "object_id": 2, "content_type_id": 2, "state": "published"})
    return db


def _titles(db):
    return {row["id"]: row["title"] for row in db[STORY_CONTENT_TABLE].all()}


def test_only_stories_the_site_shows_keep_their_text(tmp_path, keep_public_content):
    db = _stories_database(
        tmp_path / "stories.db",
        [
            ("PUBLISHED", "published", NOW - timedelta(days=1), None),
            ("DRAFT", "draft", None, None),
            ("SCHEDULED", "published", NOW + timedelta(days=30), None),
            ("EXPIRED", "published", NOW - timedelta(days=60), NOW - timedelta(days=30)),
            ("UNPUBLISHED", "unpublished", NOW - timedelta(days=1), None),
        ],
    )

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {})

    assert _titles(db) == {1: "PUBLISHED", 2: "example", 3: "example", 4: "example", 5: "example"}


def test_a_kept_story_loses_its_byline(tmp_path, keep_public_content):
    db = _stories_database(tmp_path / "stories.db", [("PUBLISHED", "published", None, None)])

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {})

    row = db[STORY_CONTENT_TABLE].find_one(id=1)
    assert row["post_text"] == "<p>Autorius: example, example</p><p>TEKSTAS</p>"
    assert row["abstract"] == "<p>Autorius: example, example</p><p>SANTRAUKA</p>"


def test_without_the_flag_every_story_is_scrubbed(tmp_path):
    db = _stories_database(tmp_path / "stories.db", [("PUBLISHED", "published", None, None)])

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {})

    assert _titles(db) == {1: "example"}


def test_without_versioning_no_story_counts_as_published(tmp_path, keep_public_content):
    db = _stories_database(tmp_path / "stories.db", [("PUBLISHED", "published", None, None)])
    db["djangocms_versioning_version"].drop()

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {})

    assert _titles(db) == {1: "example"}


def test_a_public_news_item_keeps_its_text_but_not_its_author(tmp_path, keep_public_content):
    db = dataset.connect(f"sqlite:///{tmp_path / 'news.db'}")
    common = {"body": f"{BYLINE}<p>NAUJIENA</p>", "summary": BYLINE, "author_name": "Ona Onaite", "author": "x"}
    db["news_item"].insert_many(
        [
            {"id": 1, "title": "PUBLIC", "slug": "public", "is_public": True, "deleted": False, **common},
            {"id": 2, "title": "PRIVATE", "slug": "private", "is_public": False, "deleted": False, **common},
            {"id": 3, "title": "DELETED", "slug": "deleted", "is_public": True, "deleted": True, **common},
        ]
    )

    _anonymize_news_item(db, Faker(), Mock(), {})

    rows = {row["id"]: row for row in db["news_item"].all()}
    assert [rows[pk]["title"] for pk in (1, 2, 3)] == ["PUBLIC", "example", "example"]
    assert rows[1]["body"] == "<p>Autorius: example, example</p><p>NAUJIENA</p>"
    assert all(row["author_name"] == "example, example" and row["author"] is None for row in rows.values())


def test_a_published_but_deleted_page_is_scrubbed(tmp_path, keep_public_content):
    db = dataset.connect(f"sqlite:///{tmp_path / 'pages.db'}")
    common = {"body": "<p>TEKSTAS</p>", "description": "", "slug": "page"}
    db["adp_cms_page"].insert_many(
        [
            {"id": 1, "title": "PUBLISHED", "published": True, "deleted": False, **common},
            {"id": 2, "title": "DELETED", "published": True, "deleted": True, **common},
            {"id": 3, "title": "DRAFT", "published": False, "deleted": False, **common},
        ]
    )

    _anonymize_adp_cms_page(db, Faker(), Mock(), {})

    assert [row["title"] for row in db["adp_cms_page"].all()] == ["PUBLISHED", "example", "example"]
