import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from cms.api import create_page
from cms.models import Page
from cms.apphook_pool import apphook_pool
from cms.models import PageContent, PageUrl
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.db import transaction
from djangocms_stories.cms_appconfig import StoriesConfig, config_defaults
from djangocms_versioning.models import Version


LANGUAGE = "lt"
# Spelled out rather than left to INHERIT: the pages that have no parent have
# nothing to inherit from, and django-cms would fall back to the first entry in
# CMS_TEMPLATES, which is this one anyway.
TEMPLATE = "pages/page.html"

# Matches the configuration on production, including the template prefix - that
# is what makes the stories views use vitrina/cms/post_*.html instead of the
# package's own templates.
STORIES_CONFIG = {
    "namespace": "Blog",
    "app_title": "Blog",
    "object_name": "Article",
    "template_prefix": "vitrina/cms",
}

# The page tree as production has it. Order matters: a parent has to be created
# before the children that name it.
#
# "Home" is not a page anyone sees - / is served by vitrina.views.home, a plain
# Django view registered before cms.urls. It exists to be the root of the tree:
# marking it home strips its slug from its descendants, which is why the blog
# lives at /blog/ rather than /home/blog/.
PAGES = [
    {"title": "Home", "slug": "home", "is_home": True},
    {"title": "Blog", "slug": "blog", "parent": "home", "stories_config": True},
    {"title": "Duomenų ištekliai", "slug": "datasets", "in_navigation": True},
    {"title": "Poreikiai ir pasiūlymai", "slug": "requests/submitted", "in_navigation": True},
    {"title": "Pagalba atvėrėjams", "slug": "opening-tips", "in_navigation": True},
    {"title": "Atvirų duomenų saugykla", "slug": "saugykla", "parent": "opening-tips", "in_navigation": True},
    {"title": "Duomenų atvėrimo vadovas", "slug": "vadovas", "parent": "opening-tips", "in_navigation": True},
    {"title": "Duomenų struktūros aprašas", "slug": "aprasas", "parent": "opening-tips", "in_navigation": True},
    {
        "title": "Įrankiai duomenų atvėrimui",
        "slug": "data-opening-tools",
        "parent": "opening-tips",
        "in_navigation": True,
    },
    {
        "title": "Mokymo medžiaga",
        "slug": "opening/learningmaterial",
        "parent": "opening-tips",
        "in_navigation": True,
    },
    {
        "title": "Poreikio peradresavimas kitai organizacijai/-oms",
        "slug": "poreikio-peradresavimas-kitai-organizacijai-oms",
        "parent": "opening/learningmaterial",
        "in_navigation": True,
    },
    {"title": "Dažnai užduodami klausimai", "slug": "opening_faq", "parent": "opening-tips", "in_navigation": True},
    {
        "title": "Koordinatoriaus ir tvarkytojo registravimas",
        "slug": "koordinatoriaus-ir-tvarkytojo-registravimas",
        "parent": "opening-tips",
        "in_navigation": True,
    },
    {
        "title": "Duomenų atvėrimo principai",
        "slug": "duomenu-atverimo-principai",
        "parent": "opening-tips",
        "in_navigation": True,
    },
    {"title": "Daugiau", "slug": "more", "in_navigation": True},
    {"title": "Reglamentacija", "slug": "regulation", "parent": "more", "in_navigation": True},
    {"title": "Teisės aktai", "slug": "regulation_legal", "parent": "regulation", "in_navigation": True},
    {"title": "Privatumo politika", "slug": "regulation_strat", "parent": "regulation", "in_navigation": True},
    {"title": "Panaudojimo atvejai", "slug": "usecases/examples", "parent": "more", "in_navigation": True},
    {"title": "Nuorodos", "slug": "nuorodos", "parent": "more", "in_navigation": True},
    {"title": "Apie", "slug": "about", "parent": "more", "in_navigation": True},
    {"title": "Kontaktai", "slug": "contacts", "parent": "more", "in_navigation": True},
    {"title": "Kiti AD portalai", "slug": "other", "parent": "more", "in_navigation": True},
    {"title": "SPARQL paieška", "slug": "sparql-paieska", "parent": "more", "in_navigation": True},
    # Production overrides this one's url: the page sits under "more" but answers
    # at /partner/api/1/.
    {
        "title": "API",
        "slug": "partnerapi1",
        "parent": "more",
        "in_navigation": True,
        "overwrite_url": "partner/api/1",
    },
    {
        "title": "Programinės įrangos atnaujinimai",
        "slug": "programines-irangos-atnaujinimai",
        "parent": "more",
        "in_navigation": True,
    },
    {
        "title": "Spintos atnaujinimai",
        "slug": "spintos-atnaujinimai",
        "parent": "programines-irangos-atnaujinimai",
        "in_navigation": True,
    },
    {
        "title": "Katalogo atnaujinimai",
        "slug": "katalogo-atnaujinimai",
        "parent": "programines-irangos-atnaujinimai",
        "in_navigation": True,
    },
    {
        "title": "Kaip atnaujinti SPINTA agentą",
        "slug": "kaip-atnaujinti-spinta-agenta",
        "parent": "programines-irangos-atnaujinimai",
        "in_navigation": True,
    },
    {"title": "Naujienos", "slug": "news", "in_navigation": True},
    {"title": "Sveikatos duomenys", "slug": "sveikatos-duomenys", "in_navigation": True},
]


def get_or_create_stories_config():
    apphook_pool.discover_apps()
    config, created = StoriesConfig.objects.get_or_create(
        namespace=STORIES_CONFIG["namespace"],
        defaults={**config_defaults, "template_prefix": STORIES_CONFIG["template_prefix"]},
    )
    if created:
        config.set_current_language(LANGUAGE)
        config.app_title = STORIES_CONFIG["app_title"]
        config.object_name = STORIES_CONFIG["object_name"]
        config.save()
        print(f"  Created StoriesConfig: '{STORIES_CONFIG['app_title']}' (namespace={STORIES_CONFIG['namespace']!r})")
    else:
        print(f"  StoriesConfig already exists, skipping (namespace={STORIES_CONFIG['namespace']!r})")
    return config


def run():
    site = Site.objects.get_current()
    User = get_user_model()
    superuser = User.objects.filter(is_superuser=True).first()
    if superuser is None:
        raise SystemExit("No superuser found — create one first with createsuperuser")

    print(f"Creating pages on site: {site} (publishing as '{superuser}')")

    home_page = None
    stories_config = get_or_create_stories_config()

    existing_slugs = set(
        PageUrl.objects.filter(
            slug__in=[p["slug"] for p in PAGES if p.get("slug")],
            page__site=site,
            language=LANGUAGE,
        ).values_list("slug", flat=True)
    )

    created_count = 0
    by_slug = {}
    for page_def in PAGES:
        title = page_def["title"]
        slug = page_def.get("slug")
        in_navigation = page_def.get("in_navigation", False)
        attach_stories = page_def.get("stories_config", False)
        is_home = page_def.get("is_home", False)
        parent_slug = page_def.get("parent")
        overwrite_url = page_def.get("overwrite_url")

        if slug in existing_slugs:
            # Remember it anyway: pages further down name it as their parent.
            existing = Page.objects.filter(urls__slug=slug, urls__language=LANGUAGE, site=site).first()
            if existing:
                by_slug[slug] = existing
            print(f"  Skipping '{title}' — slug {slug!r} already exists")
            continue

        parent = by_slug.get(parent_slug) if parent_slug else None
        if parent_slug and parent is None:
            raise SystemExit(f"'{title}' asks for parent {parent_slug!r}, which is not in the tree above it")

        page = create_page(
            title=title,
            template=TEMPLATE,
            language=LANGUAGE,
            slug=slug,
            in_navigation=in_navigation,
            site=site,
            created_by=superuser,
            parent=parent,
            apphook="StoriesApp" if attach_stories else None,
            apphook_namespace=stories_config.namespace if attach_stories else None,
            overwrite_url=overwrite_url,
        )
        by_slug[slug] = page

        if is_home:
            # cms locks the tree roots while it rewrites the descendants' paths,
            # and that lock needs a transaction of its own.
            with transaction.atomic():
                page.set_as_homepage()
            home_page = page
        content = PageContent.admin_manager.get(page=page, language=LANGUAGE)
        version = Version.objects.get_for_content(content)
        version.publish(user=superuser)

        label = f"slug={slug!r}"
        if parent_slug:
            label += f", parent={parent_slug!r}"
        if is_home:
            label += ", home"
        if attach_stories:
            label += f", apphook=StoriesApp/{stories_config.namespace}"
        print(f"  Created + published: '{title}' ({label})")
        created_count += 1

    if home_page:
        print(f"Homepage set to: '{home_page.get_title()}'")
    print(f"\nDone. {created_count} page(s) created, {len(PAGES) - created_count} skipped.")


if __name__ == "__main__":
    run()
