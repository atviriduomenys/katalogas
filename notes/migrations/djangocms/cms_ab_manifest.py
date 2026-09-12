"""A/B manifesto generatorius django-cms 3 -> 5 migracijos validavimui (DAS-428).

Kodėl manifestas, o ne SQL palyginimas: stendų schemos skirtingos
(`djangocms_blog_*` vs `djangocms_stories_*`, `cms_title` vs `cms_pagecontent`),
tad ta pati užklausa ten neveiks. Šis skriptas iš abiejų pusių generuoja
**vienodos formos** JSON, ir lyginami manifestai, ne lentelės.

Paleidimas (abiejuose stenduose vienodai). Python skaito failą iš standartinės įvesties, tad
konteineryje jo nereikia, o `vitrina` importuojama iš konteinerio darbinio katalogo:

    docker compose exec -T vitrina python - < notes/migrations/djangocms/cms_ab_manifest.py > manifest-a.json

Svarbiausias tikrinamas dalykas — `published` laukas. Tyliausias migracijos gedimas:
publikuotas puslapis po versioning migracijos nukrenta į DRAFT ir dingsta iš svetainės
be jokios klaidos. Manifeste tai matosi kaip published: true -> false.
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
    """Plugin'ų kiekiai pagal tipą — {"TextPlugin": 3, "SideMenuPlugin": 1}."""
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
    # Public tree: CMS 3 laiko draft/public poras, mums rūpi tai, ką mato lankytojas.
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
                    # tree_path = medžio (materialized path) reikšmė. Tai vienintelis tapatybės
                    # laukas, kurį migracija garantuotai išsaugo: cms.0037 būtent node.path
                    # nukopijuoja į Page.path. URL kelias tam netinka — neišverstas puslapis
                    # duoda tuščią kelią ir susiduria su šakniniu.
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
        # admin_manager: kitaip nematytume nepublikuotų PageContent, o mums svarbu
        # užfiksuoti ir juos - būtent jų atsiradimas reikštų nutylėtą regresiją.
        #
        # Grupuojam pagal kalbą: versionavime tam pačiam puslapiui ta pačia kalba gali
        # egzistuoti IR published, IR draft PageContent (kai prieš migraciją buvo
        # neišsaugotų redagavimų). A pusėje tai buvo viena eilutė, tad sujungiam - kitaip
        # raktas dubliuotųsi ir palyginimas melagingai rodytų „nukrito į draft".
        by_language = {}
        for content in PageContent.admin_manager.filter(page=page):
            by_language.setdefault(content.language, []).append(content)

        for lang, contents in by_language.items():
            if languages and lang not in languages:
                continue
            published = [c for c in contents if _content_state(c) == PUBLISHED]
            # Atstovas — publikuota versija, jei tokia yra; kitaip naujausia.
            content = published[0] if published else max(contents, key=lambda c: c.pk)
            is_published = page.pk in published_ids and bool(published)
            rows.append(
                {
                    "language": lang,
                    # cms5 pusėje medžio kelias jau gyvena pačiame Page (TreeNode sulietas).
                    "tree_path": page.path,
                    "slug": page.get_slug(language=lang, fallback=False),
                    "path": page.get_path(language=lang, fallback=False),
                    "title": content.title,
                    "parent_path": parent.get_path(language=lang, fallback=True) if parent else None,
                    "depth": page.depth,
                    "published": is_published,
                    # Neišsaugoti juodraščiai šalia publikuotos versijos — ne gedimas,
                    # bet verta matyti: būtent juos migracija ir turi išsaugoti.
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


# --------------------------------------------------------------------------- bendra

def _iso(value):
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _author(user):
    """Autorių lyginam pagal prisijungimo vardą, ne pk — pk gali pasislinkti perkeliant.

    `get_username()`, ne `.username`: portalo `User` turi `username = None` ir prisijungia el. paštu, tad
    `.username` visur būtų None, o autoriaus pasikeitimo patikra — tuščia.
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
