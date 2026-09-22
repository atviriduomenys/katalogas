"""The acceptance gate for the django-cms migration: a broken check lets a bad migration pass."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "notes" / "migrations" / "djangocms" / "cms_ab_diff.py"
_spec = importlib.util.spec_from_file_location("cms_ab_diff", SCRIPT)
cms_ab_diff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cms_ab_diff)


def page(**changes):
    row = {
        "language": "lt",
        "tree_path": "0001",
        "slug": "apie",
        "path": "apie",
        "title": "Apie",
        "parent_path": None,
        "depth": 1,
        "published": True,
        "in_navigation": True,
        "template": "pages/page.html",
        "redirect": None,
        "plugins": {"TextPlugin": 2},
    }
    return {**row, **changes}


def post(**changes):
    row = {
        "language": "lt",
        "slug": "naujiena",
        "title": "Naujiena",
        "published": True,
        "date_published": "2026-01-01T10:00:00+00:00",
        "author": "redaktorius@example.com",
        "categories": [1],
    }
    return {**row, **changes}


def manifest(pages=(), posts=(), stack="cms3"):
    return {"stack": stack, "counts": {}, "pages": list(pages), "posts": list(posts)}


def check(a_pages=(), b_pages=(), a_posts=(), b_posts=()):
    return cms_ab_diff.compare(manifest(a_pages, a_posts), manifest(b_pages, b_posts, stack="cms5"))


def test_an_unchanged_manifest_passes_clean():
    assert check([page()], [page()], [post()], [post()]) == ([], [])


def test_a_missing_page_blocks():
    blocking, _ = check([page()], [])

    assert any("PAGE GONE" in line for line in blocking)


def test_a_new_page_is_only_informational():
    blocking, info = check([], [page()])

    assert blocking == []
    assert any("new page" in line for line in info)


@pytest.mark.parametrize(
    "before, after, expected",
    [(True, False, "DROPPED TO DRAFT"), (False, True, "UNEXPECTEDLY PUBLISHED")],
)
def test_a_page_changing_publication_state_blocks(before, after, expected):
    blocking, _ = check([page(published=before)], [page(published=after)])

    assert any(expected in line for line in blocking)


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("slug", "apie-mus", "SLUG changed"),
        ("path", "apie-mus", "URL changed"),
        ("parent_path", "kita", "TREE changed"),
        ("in_navigation", False, "NAVIGATION changed"),
        ("plugins", {"TextPlugin": 1}, "PLUGINS GONE"),
        ("redirect", None, "REDIRECT GONE"),
    ],
)
def test_a_page_change_that_breaks_the_site_blocks(field, value, expected):
    before = page(redirect="/kitur/") if field == "redirect" else page()

    blocking, _ = check([before], [page(**{field: value})])

    assert any(expected in line for line in blocking)


@pytest.mark.parametrize(
    "changes",
    [{"title": "Apie mus"}, {"plugins": {"TextPlugin": 2, "SideMenuPlugin": 1}}, {"redirect": "/kitur/"}],
)
def test_a_page_change_that_loses_nothing_is_only_informational(changes):
    before = page(redirect="/anksciau/") if "redirect" in changes else page()

    blocking, info = check([before], [page(**changes)])

    assert blocking == []
    assert len(info) == 1


def test_pages_are_matched_by_tree_path_not_url():
    """Untranslated pages have an empty URL path, like the root; they must not collide."""
    root = page(tree_path="0001", path="", slug="")
    untranslated = page(tree_path="0002", path="", slug="")

    assert check([root, untranslated], [root, untranslated]) == ([], [])


def test_a_duplicate_key_stops_the_comparison():
    with pytest.raises(ValueError, match="Duplicate key"):
        check([page(), page()], [page()])


def test_a_missing_article_blocks():
    blocking, _ = check(a_posts=[post()], b_posts=[])

    assert any("ARTICLE GONE" in line for line in blocking)


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({"published": False}, "ARTICLE dropped to draft"),
        ({"date_published": "2026-02-01T10:00:00+00:00"}, "ARTICLE date changed"),
        ({"author": "kitas@example.com"}, "ARTICLE author changed"),
    ],
)
def test_an_article_change_blocks(changes, expected):
    blocking, _ = check(a_posts=[post()], b_posts=[post(**changes)])

    assert any(expected in line for line in blocking)


def test_an_article_published_by_the_migration_blocks():
    blocking, _ = check(a_posts=[post(published=False)], b_posts=[post()])

    assert any("ARTICLE UNEXPECTEDLY PUBLISHED" in line for line in blocking)


@pytest.mark.parametrize("after, exit_code", [(page(), 0), (page(published=False), 1)])
def test_the_exit_code_is_what_a_deployment_script_reads(tmp_path, after, exit_code):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(manifest([page()])))
    b.write_text(json.dumps(manifest([after], stack="cms5")))

    result = subprocess.run([sys.executable, str(SCRIPT), str(a), str(b)], capture_output=True, text=True)

    assert result.returncode == exit_code, result.stdout + result.stderr
