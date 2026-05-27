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
from djangocms_stories.cms_appconfig import StoriesConfig, config_defaults
from djangocms_versioning.models import Version


LANGUAGE = "lt"
TEMPLATE = "INHERIT"

STORIES_CONFIG = {
    "namespace": "blog",
    "app_title": "Tiklaraštis",
}

PAGES = [
    {
        "title": "Duomenų ištekliai",
        "slug": "datasets",
        "in_navigation": True,
    },
    {
        "title": "Naujienos",
        "slug": "naujienos",
        "in_navigation": True,
        "stories_config": True,
    },
    {
        "title": "Mokymai",
        "slug": "mokymai",
        "in_navigation": True,
    },
]


def get_or_create_stories_config():
    apphook_pool.discover_apps()
    config, created = StoriesConfig.objects.get_or_create(
        namespace=STORIES_CONFIG["namespace"],
        defaults=config_defaults,
    )
    if created:
        config.set_current_language(LANGUAGE)
        config.app_title = STORIES_CONFIG["app_title"]
        config.save()
        print(f"  Created StoriesConfig: '{STORIES_CONFIG['app_title']}' (namespace={STORIES_CONFIG['namespace']!r})")
    else:
        print(f"  StoriesConfig already exists, skipping (namespace={STORIES_CONFIG['namespace']!r})")
    return config

def get_or_create_stories_config():
    apphook_pool.discover_apps()
    config, created = StoriesConfig.objects.get_or_create(
        namespace=STORIES_CONFIG["namespace"],
        defaults=config_defaults,
    )
    if created:
        config.set_current_language(LANGUAGE)
        config.app_title = STORIES_CONFIG["app_title"]
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
            slug__in=[p["slug"] for p in PAGES if p.get("slug")]
        ).values_list("slug", flat=True)
    )

    created_count = 0
    for page_def in PAGES:
        title = page_def["title"]
        slug = page_def.get("slug")
        in_navigation = page_def.get("in_navigation", False)
        attach_stories = page_def.get("stories_config", False)

        if slug in existing_slugs:
            print(f"  Skipping '{title}' — slug {slug!r} already exists")
            continue

        page = create_page(
            title=title,
            template=TEMPLATE,
            language=LANGUAGE,
            slug=slug,
            in_navigation=in_navigation,
            site=site,
            created_by=superuser,
            apphook="StoriesApp" if attach_stories else None,
            apphook_namespace=stories_config.namespace if attach_stories else None,
            published=True,
        )

        if is_home:
            page.set_as_homepage()
            home_page = page
        content = PageContent.admin_manager.get(page=page, language=LANGUAGE)
        version = Version.objects.get_for_content(content)
        version.publish(user=superuser)

        print(f"  Created: '{title}' (slug={slug!r}, is_home={is_home})")
        label = f"slug={slug!r}"
        if attach_stories:
            label += f", apphook=StoriesApp/{stories_config.namespace}"
        print(f"  Created + published: '{title}' ({label})")
        created_count += 1

    print(f"\nDone. {len(PAGES)} pages created.")
    if home_page:
        print(f"Homepage set to: '{home_page.get_title()}'")
    print(f"\nDone. {created_count} page(s) created, {len(PAGES) - created_count} skipped.")


if __name__ == "__main__":
    run()
