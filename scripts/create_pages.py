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
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version


LANGUAGE = "lt"
# Root pages have nothing to inherit from, and this is CMS_TEMPLATES[0] anyway.
TEMPLATE = "pages/page.html"

# Matches production. template_prefix is what makes the stories views use
# vitrina/cms/post_*.html.
STORIES_CONFIG = {
    "namespace": "Blog",
    "app_title": "Blog",
    "object_name": "Article",
    "template_prefix": "vitrina/cms",
}

# The page tree as production has it. "Home" is marked home so its slug drops out of
# its descendants' URLs (/blog/, not /home/blog/); / itself is vitrina.views.home.
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
    # Sits under "more", but production answers it at /partner/api/1/.
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


def _finish_what_a_broken_run_left(page, is_home, superuser):
    """Publish a page an interrupted run left as a draft with no published version.

    A published page with a newer draft is someone's edit, so it is left alone.
    """
    if is_home and not page.is_home:
        with transaction.atomic():
            page.set_as_homepage()
        print(f"  Made '{page.get_title()}' the home page, which an earlier run left undone")
    if PageContent.objects.filter(page=page, language=LANGUAGE).exists():
        return
    draft = PageContent.admin_manager.filter(page=page, language=LANGUAGE).first()
    version = Version.objects.get_for_content(draft) if draft else None
    if version is not None and version.state == DRAFT:
        version.publish(user=superuser)
        print(f"  Published the draft an earlier run left behind for '{page.get_title()}'")


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
                _finish_what_a_broken_run_left(existing, is_home, superuser)
                if is_home:
                    home_page = existing
            print(f"  Skipping '{title}' — slug {slug!r} already exists")
            continue

        parent = by_slug.get(parent_slug) if parent_slug else None
        if parent_slug and parent is None:
            raise SystemExit(f"'{title}' asks for parent {parent_slug!r}, which is not in the tree above it")

        # One transaction per page: create_page commits on its own, so a failure before
        # publish() left a draft that every later run skipped. set_as_homepage needs it too.
        with transaction.atomic():
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
            if is_home:
                page.set_as_homepage()
            content = PageContent.admin_manager.get(page=page, language=LANGUAGE)
            Version.objects.get_for_content(content).publish(user=superuser)
        by_slug[slug] = page
        if is_home:
            home_page = page

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
