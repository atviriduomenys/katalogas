"""--keep-public-content spares only what the site shows, and never the byline."""

import inspect
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import dataset
from faker import Faker

from scripts import anonymize
from scripts.anonymize import (
    PUBLIC_CONTENT_TABLES,
    STORY_CONTENT_TABLE,
    _anonymize_adp_cms_page,
    _anonymize_djangocms_stories_postcontent,
    _anonymize_news_item,
    _published_story_content_ids,
    _scrub_story_plugins,
)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
BYLINE = "<p>Autorius: Jonas Jonaitis</p>"


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


def test_only_stories_the_site_shows_keep_their_text(tmp_path):
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

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {}, keep_public_content=True)

    assert _titles(db) == {1: "PUBLISHED", 2: "example", 3: "example", 4: "example", 5: "example"}


def test_a_kept_story_loses_its_byline(tmp_path):
    db = _stories_database(tmp_path / "stories.db", [("PUBLISHED", "published", None, None)])

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {}, keep_public_content=True)

    row = db[STORY_CONTENT_TABLE].find_one(id=1)
    assert row["post_text"] == "<p>Autorius: example, example</p><p>TEKSTAS</p>"
    assert row["abstract"] == "<p>Autorius: example, example</p><p>SANTRAUKA</p>"


def test_without_the_flag_every_story_is_scrubbed(tmp_path):
    db = _stories_database(tmp_path / "stories.db", [("PUBLISHED", "published", None, None)])

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {})

    assert _titles(db) == {1: "example"}


def test_without_versioning_no_story_counts_as_published(tmp_path):
    db = _stories_database(tmp_path / "stories.db", [("PUBLISHED", "published", None, None)])
    db["djangocms_versioning_version"].drop()

    _anonymize_djangocms_stories_postcontent(db, Faker(), Mock(), {}, keep_public_content=True)

    assert _titles(db) == {1: "example"}


def _add_text_plugin(db, pk, content_type_id, object_id, body):
    db["cms_placeholder"].insert({"id": pk, "content_type_id": content_type_id, "object_id": object_id})
    db["cms_cmsplugin"].insert({"id": pk, "placeholder_id": pk})
    db["djangocms_text_text"].insert({"cmsplugin_ptr_id": pk, "body": body})


def test_a_kept_story_keeps_its_placeholder_text(tmp_path):
    """A config with use_placeholder renders the placeholder, not post_text."""
    db = _stories_database(
        tmp_path / "stories.db",
        [("PUBLISHED", "published", None, None), ("DRAFT", "draft", None, None)],
    )
    _add_text_plugin(db, 1, content_type_id=1, object_id=1, body=f"{BYLINE}<p>TEKSTAS</p>")
    _add_text_plugin(db, 2, content_type_id=1, object_id=2, body="<p>JUODRASTIS</p>")
    _add_text_plugin(db, 3, content_type_id=2, object_id=1, body="<p>PUSLAPIS</p>")

    _scrub_story_plugins(db, _published_story_content_ids(db))

    bodies = {row["cmsplugin_ptr_id"]: row["body"] for row in db["djangocms_text_text"].all()}
    assert bodies == {
        1: "<p>Autorius: example, example</p><p>TEKSTAS</p>",
        2: "<p>example</p>",
        3: "<p>PUSLAPIS</p>",
    }


def test_a_public_news_item_keeps_its_text_but_not_its_author(tmp_path):
    db = dataset.connect(f"sqlite:///{tmp_path / 'news.db'}")
    common = {"body": f"{BYLINE}<p>NAUJIENA</p>", "summary": BYLINE, "author_name": "Ona Onaite", "author": "x"}
    db["news_item"].insert_many(
        [
            {"id": 1, "title": "PUBLIC", "slug": "public", "is_public": True, "deleted": False, **common},
            {"id": 2, "title": "PRIVATE", "slug": "private", "is_public": False, "deleted": False, **common},
            {"id": 3, "title": "DELETED", "slug": "deleted", "is_public": True, "deleted": True, **common},
        ]
    )

    _anonymize_news_item(db, Faker(), Mock(), {}, keep_public_content=True)

    rows = {row["id"]: row for row in db["news_item"].all()}
    assert [rows[pk]["title"] for pk in (1, 2, 3)] == ["PUBLIC", "example", "example"]
    assert rows[1]["body"] == "<p>Autorius: example, example</p><p>NAUJIENA</p>"
    assert all(row["author_name"] == "example, example" and row["author"] is None for row in rows.values())


def test_a_published_but_deleted_page_is_scrubbed(tmp_path):
    db = dataset.connect(f"sqlite:///{tmp_path / 'pages.db'}")
    common = {"body": "<p>TEKSTAS</p>", "description": "", "slug": "page"}
    db["adp_cms_page"].insert_many(
        [
            {"id": 1, "title": "PUBLISHED", "published": True, "deleted": False, **common},
            {"id": 2, "title": "DELETED", "published": True, "deleted": True, **common},
            {"id": 3, "title": "DRAFT", "published": False, "deleted": False, **common},
        ]
    )

    _anonymize_adp_cms_page(db, Faker(), Mock(), {}, keep_public_content=True)

    assert [row["title"] for row in db["adp_cms_page"].all()] == ["PUBLISHED", "example", "example"]


def test_every_public_content_table_takes_the_flag():
    """main() passes keep_public_content to these by name, so a missing parameter is a crash."""
    for table in PUBLIC_CONTENT_TABLES:
        assert "keep_public_content" in inspect.signature(getattr(anonymize, f"_anonymize_{table}")).parameters
