"""scripts/create_pages.py needs parents before children, unique slugs and one home page.

Otherwise it breaks, and only when run against an empty database.
"""

from collections import Counter

from scripts.create_pages import PAGES


def test_every_parent_is_listed_before_its_children():
    seen = set()
    for page in PAGES:
        parent = page.get("parent")
        assert parent is None or parent in seen, f"{page['slug']!r} names a parent listed after it"
        seen.add(page["slug"])


def test_slugs_are_unique():
    counts = Counter(page["slug"] for page in PAGES)
    assert [slug for slug, n in counts.items() if n > 1] == []


def test_exactly_one_page_is_the_home_page():
    homes = [page["slug"] for page in PAGES if page.get("is_home")]

    # Two home pages and the last wins silently; none and the blog moves to /home/blog/.
    assert homes == ["home"]


def test_the_blog_hangs_under_home_and_carries_the_apphook():
    blog = next(page for page in PAGES if page["slug"] == "blog")

    assert blog["parent"] == "home"
    assert blog["stories_config"] is True
