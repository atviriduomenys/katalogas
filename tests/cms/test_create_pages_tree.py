"""The page tree in scripts/create_pages.py has to stay usable.

The script builds pages in the order they are listed and looks parents up by
slug, so a child listed above its parent, a repeated slug or a second home page
all break it - and only when someone runs it against an empty database.
"""

from collections import Counter


def _pages():
    from scripts.create_pages import PAGES

    return PAGES


def test_every_parent_is_listed_before_its_children():
    seen = set()
    for page in _pages():
        parent = page.get("parent")
        assert parent is None or parent in seen, f"{page['slug']!r} names a parent listed after it"
        seen.add(page["slug"])


def test_slugs_are_unique():
    counts = Counter(page["slug"] for page in _pages())
    assert [slug for slug, n in counts.items() if n > 1] == []


def test_exactly_one_page_is_the_home_page():
    homes = [page["slug"] for page in _pages() if page.get("is_home")]

    # More than one and the last wins silently; none and the blog ends up at
    # /home/blog/ instead of /blog/, as production has it.
    assert homes == ["home"]


def test_the_blog_hangs_under_home_and_carries_the_apphook():
    blog = next(page for page in _pages() if page["slug"] == "blog")

    assert blog["parent"] == "home"
    assert blog["stories_config"] is True
