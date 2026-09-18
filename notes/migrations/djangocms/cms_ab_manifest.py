"""A/B manifest generator for validating the django-cms 3 -> 5 migration (DAS-428).

A manifest rather than an SQL comparison, because the two sides do not share a
schema (`djangocms_blog_*` vs `djangocms_stories_*`, `cms_title` vs
`cms_pagecontent`): the same query cannot run on both. This script emits JSON of
the **same shape** from either side, and it is the manifests that get compared.

Run it the same way on both sides. Python reads the file from stdin, so it does
not have to exist inside the container, and `vitrina` is imported from the
container's working directory:

    docker compose exec -T vitrina python - < notes/migrations/djangocms/cms_ab_manifest.py > manifest-a.json

The field that matters most is `published`. The quietest way this migration can
fail is a published page dropping to DRAFT and disappearing from the site
without an error; in the manifest that shows up as published: true -> false.
"""

import json
import os
import sys

import django


def _setup():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
    django.setup()


def _detect_stack():
    """cms3 = TreeNode + djangocms_blog; cms5 = PageContent + djangocms_stories."""
    from django.apps import apps

    if apps.is_installed("djangocms_versioning"):
        return "cms5"
    return "cms3"


def _plugin_counts(placeholders, language):
    """Plugin counts per type - {"TextPlugin": 3, "SideMenuPlugin": 1}."""
    counts = {}
    for ph in placeholders:
        try:
            plugins = ph.get_plugins(language) if language else ph.get_plugins()
        except TypeError:
            plugins = ph.get_plugins()
        for plugin in plugins:
            counts[plugin.plugin_type] = counts.get(plugin.plugin_type, 0) + 1
    return dict(sorted(counts.items()))


# --------------------------------------------------------------------------- cms 3

def _pages_cms3(languages):
    from cms.models import Page

    rows = []
    # The public tree: CMS 3 keeps draft/public pairs, and what a visitor sees is the public one.
    for page in Page.objects.filter(publisher_is_draft=False).order_by("node__path"):
        node = page.node
        parent_node = node.get_parent() if node else None
        parent = parent_node.item if parent_node is not None else None
        for lang in page.get_languages():
            if languages and lang not in languages:
                continue
            rows.append(
                {
                    "language": lang,
                    # The materialized tree path is the one identity the migration is
                    # guaranteed to preserve: cms.0037 copies node.path into Page.path.
                    # The URL path will not do - an untranslated page has an empty one
                    # and collides with the root.
                    "tree_path": node.path if node else None,
                    "slug": page.get_slug(language=lang, fallback=False),
                    "path": page.get_path(language=lang, fallback=False),
                    "title": page.get_title(language=lang, fallback=False),
                    "parent_path": parent.get_path(language=lang, fallback=True) if parent else None,
                    "depth": node.depth if node else None,
                    "published": page.is_published(lang),
                    "in_navigation": page.in_navigation,
                    "template": page.get_template(),
                    "redirect": page.get_redirect(language=lang, fallback=False),
                    "plugins": _plugin_counts(page.placeholders.all(), lang),
                }
            )
    return rows


def _posts_cms3(languages):
    from djangocms_blog.models import Post

    rows = []
    for post in Post.objects.all().order_by("pk"):
        for lang in post.get_available_languages():
            if languages and lang not in languages:
                continue
            post.set_current_language(lang)
            rows.append(
                {
                    "language": lang,
                    "slug": post.slug,
                    "title": post.title,
                    "published": bool(post.publish and post.date_published),
                    "date_published": _iso(getattr(post, "date_published", None)),
                    "author": _author(getattr(post, "author", None)),
                    "categories": sorted(c.pk for c in post.categories.all()),
                }
            )
    return rows


# --------------------------------------------------------------------------- cms 5

def _pages_cms5(languages):
    from cms.models import Page, PageContent
    from djangocms_versioning.constants import PUBLISHED

    published_ids = set(
        PageContent.objects.filter(versions__state=PUBLISHED).values_list("page_id", flat=True)
    )
    rows = []
    for page in Page.objects.order_by("path"):
        parent = page.parent
        # admin_manager, or unpublished PageContent stays invisible - and one appearing
        # where the A side had none is exactly the regression worth recording.
        #
        # Grouped by language: under versioning one page in one language can hold a
        # published AND a draft PageContent (when edits were left unsaved before the
        # migration). The A side had a single row, so they are merged here - otherwise
        # the key would repeat and the comparison would falsely report a drop to draft.
        by_language = {}
        for content in PageContent.admin_manager.filter(page=page):
            by_language.setdefault(content.language, []).append(content)

        for lang, contents in by_language.items():
            if languages and lang not in languages:
                continue
            published = [c for c in contents if _content_state(c) == PUBLISHED]
            # The published version represents the page, or the newest one if there is none.
            content = published[0] if published else max(contents, key=lambda c: c.pk)
            is_published = page.pk in published_ids and bool(published)
            rows.append(
                {
                    "language": lang,
                    # On cms 5 the tree path lives on Page itself (TreeNode was merged in).
                    "tree_path": page.path,
                    "slug": page.get_slug(language=lang, fallback=False),
                    "path": page.get_path(language=lang, fallback=False),
                    "title": content.title,
                    "parent_path": parent.get_path(language=lang, fallback=True) if parent else None,
                    "depth": page.depth,
                    "published": is_published,
                    # Unsaved drafts next to a published version are not a failure, but
                    # they are worth seeing: preserving them is part of the job.
                    "draft_versions": len(contents) - len(published),
                    "in_navigation": content.in_navigation,
                    "template": content.template,
                    "redirect": content.redirect,
                    "plugins": _plugin_counts(content.placeholders.all(), lang),
                }
            )
    return rows


def _content_state(content):
    version = content.versions.first() if hasattr(content, "versions") else None
    return getattr(version, "state", None)


def _posts_cms5(languages):
    from djangocms_stories.models import PostContent

    rows = []
    for content in PostContent.admin_manager.all().order_by("pk"):
        lang = content.language
        if languages and lang not in languages:
            continue
        post = content.post
        rows.append(
            {
                "language": lang,
                "slug": content.slug,
                "title": content.title,
                "published": _is_published_version(content),
                "date_published": _iso(getattr(post, "date_published", None)),
                "author": _author(getattr(post, "author", None)),
                "categories": sorted(c.pk for c in post.categories.all()),
            }
        )
    return rows


def _is_published_version(obj):
    from djangocms_versioning.constants import PUBLISHED

    return _content_state(obj) == PUBLISHED


# --------------------------------------------------------------------------- shared

def _iso(value):
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _author(user):
    """Authors are compared by login name, not pk - a pk can shift when data is moved.

    `get_username()` and not `.username`: this portal's `User` has `username = None`
    and logs in by email, so `.username` would be None everywhere and the check for a
    changed author would compare nothing.
    """
    return user.get_username() if user is not None else None


def build_manifest(languages=None):
    stack = _detect_stack()
    pages = _pages_cms3(languages) if stack == "cms3" else _pages_cms5(languages)
    posts = _posts_cms3(languages) if stack == "cms3" else _posts_cms5(languages)
    return {
        "stack": stack,
        "counts": {
            "pages": len(pages),
            "pages_published": sum(1 for p in pages if p["published"]),
            "posts": len(posts),
            "posts_published": sum(1 for p in posts if p["published"]),
        },
        "pages": sorted(pages, key=lambda r: (r["tree_path"] or "", r["language"])),
        "posts": sorted(posts, key=lambda r: (r["slug"] or "", r["language"])),
    }


def main():
    _setup()
    languages = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    json.dump(build_manifest(languages), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
