import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from typing import List
from tqdm import tqdm
from typer import run
from cms.api import create_page, add_plugin, create_title, copy_plugins_to_language
from cms.models import Page
from django.urls import reverse
from vitrina.cms.models import CmsPage


def remove_home_from_navigation():
    for home_page in Page.objects.filter(is_home=True):
        home_page.in_navigation = False
        home_page.save()


def remove_blog_from_navigation():
    for blog in Page.objects.filter(application_namespace="Blog"):
        blog.in_navigation = False
        blog.save()


page_order = {
    'datasets': 1,
    'requests/submitted': 2,
    'opening-tips': 3,
    'more': 4,
    'news': 5,
    'saugykla': 6,
    'vadovas': 7,
    'aprasas': 8,
    'data-opening-tools': 9,
    'opening/learningmaterial': 10,
    'opening_faq': 11,
    'regulation': 12,
    'usecases/examples': 13,
    'nuorodos': 14,
    'savokos': 15,
    'about': 16,
    'contacts': 17,
    'other': 18,
    'sparql': 19,
    'public/api/1': 20,
    'reports': 21,
    'templates': 22,
    'regulation_legal': 23,
    'regulation_strat': 24
}


def fix_adp_pages():
    for adp_page in CmsPage.objects.filter(slug__startswith="/"):
        adp_page.slug = adp_page.slug[1:]
        adp_page.save()

    for adp_page in CmsPage.objects.all():
        if adp_page.slug == "datasets?q=&has_data=true":
            adp_page.slug = "datasets"
        elif adp_page.slug == "daugiau" or adp_page.title == "More":
            adp_page.slug = "more"
        elif adp_page.slug == "kontaktai":
            adp_page.slug = "contacts"
        elif adp_page.slug == "news":
            adp_page.parent = None
        elif adp_page.slug == "regulation_legal_en":
            if CmsPage.objects.filter(slug="regulation_legal").exclude(pk=adp_page.pk).exists():
                adp_page.parent = CmsPage.objects.filter(slug="regulation_legal")\
                    .exclude(pk=adp_page.pk).first().parent
            adp_page.slug = "regulation_legal"
        elif adp_page.slug == 'usecases/examples':
            if CmsPage.objects.filter(slug="usecases/examples", parent__isnull=False).exists():
                adp_page.parent = CmsPage.objects.filter(
                    slug="usecases/examples",
                    parent__isnull=False
                ).first().parent

        if page_order.get(adp_page.slug):
            adp_page.page_order = page_order.get(adp_page.slug)

        adp_page.save()


custom_page_settings = {
    'other': {
        'template': "pages/page.html",
        'has_side_menu': False,
        'plugins': ['EUCommissionPortalPlugin', 'EULandPlugin', 'OtherLandPlugin']
    },
    'opening/learningmaterial': {
        'plugins': ['LearningMaterialPlugin']
    },
    'opening_faq': {
        'plugins': ['FaqPlugin']
    },
    'reports': {
        'template': "pages/page.html",
        'has_side_menu': False,
        'plugins': ['ReportPlugin']
    },
    'public/api/1': {
        'redirect': reverse('public-api')
    },
    'usecases/examples': {
        'redirect': reverse('project-list')
    },
    'news': {
        'redirect': reverse('djangocms_blog:posts-latest')
    },
    'requests/submitted': {
        'redirect': reverse('request-list')
    },
    'sparql': {
        'redirect': reverse('sparql')
    },
    'datasets': {
        'redirect': reverse('dataset-list')
    }
}


def migrate_adp_page(
    adp_page: CmsPage,
    template: str = 'pages/page_with_side_menu.html',
    redirect: str = None,
    has_side_menu: bool = True,
    plugins: List[str] = None
):
    if custom_page_settings.get(adp_page.slug):
        settings = custom_page_settings[adp_page.slug]
        template = settings.get('template', template)
        redirect = settings.get('redirect', redirect)
        plugins = settings.get('plugins', plugins)
        has_side_menu = settings['has_side_menu'] if 'has_side_menu' in settings else has_side_menu

    if adp_page.parent and Page.objects.filter(title_set__slug=adp_page.parent.slug):
        parent = Page.objects.filter(title_set__slug=adp_page.parent.slug).first()
    else:
        parent = None

    page = create_page(
        title=adp_page.title,
        template=template,
        language=adp_page.language,
        slug=adp_page.slug,
        in_navigation=True,
        redirect=redirect,
        parent=parent
    )

    body_placeholder = page.placeholders.get(slot='body')
    if plugins:
        for plugin in plugins:
            add_plugin(body_placeholder, plugin, adp_page.language)
    else:
        add_plugin(body_placeholder, 'TextPlugin', adp_page.language, body=adp_page.body)

    if has_side_menu:
        menu_placeholder = page.placeholders.get(slot='side_menu')
        add_plugin(menu_placeholder, 'SideMenuPlugin', adp_page.language)

    if adp_page.published:
        page.publish(adp_page.language)


def add_language(
    adp_page: CmsPage,
    redirect: str = None,
    has_side_menu: bool = True,
    plugins: List[str] = None
):
    page = Page.objects.filter(title_set__slug=adp_page.slug).first()

    if custom_page_settings.get(adp_page.slug):
        settings = custom_page_settings[adp_page.slug]
        redirect = settings.get('redirect') or redirect
        has_side_menu = settings.get('has_side_menu') or has_side_menu
        plugins = settings.get('plugins') or plugins

    create_title(
        language=adp_page.language,
        title=adp_page.title,
        page=page,
        redirect=redirect
    )
    body_placeholder = page.placeholders.get(slot='body')
    if plugins:
        copy_plugins_to_language(
            page=page,
            source_language=page.get_languages()[0],
            target_language=adp_page.language
        )
    else:
        add_plugin(body_placeholder, 'TextPlugin', adp_page.language, body=adp_page.body)

    if has_side_menu:
        menu_placeholder = page.placeholders.get(slot='side_menu')
        add_plugin(menu_placeholder, 'SideMenuPlugin', adp_page.language)

    if adp_page.published:
        page.publish(adp_page.language)


def main():
    """
    Migrate pages to django_cms Page.
    """

    pbar = tqdm(
        "Migrating pages",
        total=CmsPage.objects.count()
    )

    remove_home_from_navigation()
    remove_blog_from_navigation()
    fix_adp_pages()

    with pbar:
        for adp_page in CmsPage.objects.all().order_by('page_order'):
            # if page with slug doesn't exist, create a new page
            if not Page.objects.filter(title_set__slug=adp_page.slug).exists():
                migrate_adp_page(adp_page)

            # if page with slug and language doesn't exist, add that language to the page
            elif not Page.objects.filter(
                title_set__slug=adp_page.slug,
                languages__icontains=adp_page.language
            ).exists():
                add_language(adp_page)
            pbar.update(1)


if __name__ == '__main__':
    run(main)
