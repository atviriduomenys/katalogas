"""Compares two A/B manifests (DAS-428) against the acceptance criteria in plan ch. 6.

    python3 notes/migrations/djangocms/cms_ab_diff.py manifest-a.json manifest-b.json

A = the reference (devel code, no cms5 migration), B = the candidate (#2646 merged
plus the migrations). Exits 1 when any criterion is broken, so CI or a script can
use it.

Not everything is compared with everything: a differing `title` is not in itself a
failure (the migration may normalise whitespace), while `published: true -> false`
is. Hence the split into BLOCKING and informational.
"""

import json
import sys


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _key(row):
    # Identity is the tree path, not the URL: an untranslated page has an empty URL
    # path and collides with the root (seen in production data).
    return (row.get("tree_path"), row.get("language"))


def _post_key(row):
    return (row.get("slug"), row.get("language"))


def _index(rows, keyfunc):
    """Indexes by key and SHOUTS if the key is not unique.

    Overwriting silently is the most dangerous failure here: a lost row would show
    up as "dropped to draft", or a missing page would go unnoticed entirely.
    """
    index = {}
    for row in rows:
        key = keyfunc(row)
        if key in index:
            raise ValueError(
                f"Duplicate key {key!r} in the manifest - identity is not unique, so the "
                f"comparison would be wrong. Fix the manifest generator."
            )
        index[key] = row
    return index


def compare(a, b):
    """Returns (blocking, info) - two lists of lines."""
    blocking = []
    info = []

    pages_a, pages_b = _index(a["pages"], _key), _index(b["pages"], _key)
    posts_a, posts_b = _index(a["posts"], _post_key), _index(b["posts"], _post_key)

    # --- pages: all still there, same slugs, same tree
    for key in sorted(set(pages_a) - set(pages_b)):
        blocking.append(f"PAGE GONE: path={key[0]!r} lang={key[1]}")
    for key in sorted(set(pages_b) - set(pages_a)):
        info.append(f"new page on the B side: path={key[0]!r} lang={key[1]}")

    for key in sorted(set(pages_a) & set(pages_b)):
        ra, rb = pages_a[key], pages_b[key]

        # The single most important check in the whole plan: published -> unpublished.
        if ra["published"] and not rb["published"]:
            blocking.append(
                f"DROPPED TO DRAFT: path={key[0]!r} lang={key[1]} (A: published, B: not)"
            )
        elif not ra["published"] and rb["published"]:
            blocking.append(
                f"UNEXPECTEDLY PUBLISHED: path={key[0]!r} lang={key[1]} (A: not, B: published) "
                f"- unpublished content would surface on the site"
            )

        if ra["slug"] != rb["slug"]:
            blocking.append(f"SLUG changed: path={key[0]!r} {ra['slug']!r} -> {rb['slug']!r}")
        if ra["path"] != rb["path"]:
            blocking.append(
                f"URL changed: tree={key[0]!r} lang={key[1]} {ra['path']!r} -> {rb['path']!r} "
                f"- old links would stop working"
            )
        if ra["parent_path"] != rb["parent_path"]:
            blocking.append(
                f"TREE changed: path={key[0]!r} parent {ra['parent_path']!r} -> {rb['parent_path']!r}"
            )
        if ra["in_navigation"] != rb["in_navigation"]:
            blocking.append(
                f"NAVIGATION changed: path={key[0]!r} "
                f"in_navigation {ra['in_navigation']} -> {rb['in_navigation']}"
            )

        if ra["plugins"] != rb["plugins"]:
            lost = {k: v for k, v in ra["plugins"].items() if rb["plugins"].get(k, 0) < v}
            if lost:
                blocking.append(f"PLUGINS GONE: path={key[0]!r} {lost}")
            else:
                info.append(f"plugin mix differs: path={key[0]!r} {ra['plugins']} -> {rb['plugins']}")

        if ra["title"] != rb["title"]:
            info.append(f"title: path={key[0]!r} {ra['title']!r} -> {rb['title']!r}")

        # A lost redirect is not cosmetic: a page that used to send the reader elsewhere
        # now serves an empty one. That is how it was found - a crawl showed 964 B replies.
        if ra["redirect"] and not rb["redirect"]:
            blocking.append(
                f"REDIRECT GONE: path={key[0]!r} lang={key[1]} {ra['redirect']!r} -> None "
                f"- the page no longer redirects, it serves an empty page"
            )
        elif ra["redirect"] != rb["redirect"]:
            info.append(f"redirect: path={key[0]!r} {ra['redirect']!r} -> {rb['redirect']!r}")

    # --- articles: all present, with their dates and authors
    for key in sorted(set(posts_a) - set(posts_b)):
        blocking.append(f"ARTICLE GONE: slug={key[0]!r} lang={key[1]}")
    for key in sorted(set(posts_b) - set(posts_a)):
        info.append(f"new article on the B side: slug={key[0]!r} lang={key[1]}")

    for key in sorted(set(posts_a) & set(posts_b)):
        ra, rb = posts_a[key], posts_b[key]
        if ra["published"] and not rb["published"]:
            blocking.append(f"ARTICLE dropped to draft: slug={key[0]!r} lang={key[1]}")
        elif not ra["published"] and rb["published"]:
            blocking.append(
                f"ARTICLE UNEXPECTEDLY PUBLISHED: slug={key[0]!r} lang={key[1]} (A: not, B: published) "
                f"- an unpublished article would surface on the site"
            )
        if ra["date_published"] != rb["date_published"]:
            blocking.append(
                f"ARTICLE date changed: slug={key[0]!r} "
                f"{ra['date_published']} -> {rb['date_published']}"
            )
        if ra["author"] != rb["author"]:
            blocking.append(
                f"ARTICLE author changed: slug={key[0]!r} {ra['author']!r} -> {rb['author']!r}"
            )

    return blocking, info


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: cms_ab_diff.py manifest-a.json manifest-b.json")

    a, b = _load(sys.argv[1]), _load(sys.argv[2])
    blocking, info = compare(a, b)

    print(f"A stack: {a['stack']}  counts: {a['counts']}")
    print(f"B stack: {b['stack']}  counts: {b['counts']}")
    print()

    if blocking:
        print(f"=== BLOCKING ({len(blocking)}) ===")
        for line in blocking:
            print(f"  ✗ {line}")
        print()
    if info:
        print(f"=== informational ({len(info)}) ===")
        for line in info:
            print(f"  · {line}")
        print()

    if blocking:
        print("RESULT: FAILED - see the blocking items.")
        sys.exit(1)

    print("RESULT: passed - structure, publication states and articles all match.")
    print("What this does not answer: whether the content still reads right (editor sign-off) and the URL crawl.")


if __name__ == "__main__":
    main()
