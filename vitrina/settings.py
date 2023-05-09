"""
Django settings for vitrina project.

Generated by 'django-admin startproject' using Django 4.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import environ
import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _


env = environ.Env()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

BASE_DB_PATH = os.path.join(BASE_DIR, 'resources/adp-pg.sql')
LOCALE_PATHS = [os.path.join(BASE_DIR, 'vitrina/locale/')]
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: Fix SECRET_KEY.
SECRET_KEY = 'django-insecure-((hv!%qj6+p@)vnuy6%(@l#0m=n*o@dy3sn3sop0m$!49^*xvy'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'data.gov.lt', 'staging.data.gov.lt']

# Application definition

INSTALLED_APPS = [
    'djangocms_admin_style',  # Django CMS

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.redirects',
    'rest_framework',
    'drf_yasg',
    'vitrina.users',

    # Django CMS
    'sass_processor',
    'sekizai',
    'cms',
    'menus',
    'treebeard',
    'filer',
    'easy_thumbnails',
    'mptt',
    'djangocms_text_ckeditor',
    'aldryn_apphooks_config',
    'parler',
    'taggit',
    'taggit_autosuggest',
    'meta',
    'sortedm2m',
    'djangocms_blog',
    'reversion',
    'hitcount',
    'crispy_forms',
    'tagulous',
    'haystack',
    'crispy_bulma',
    'chartjs',
    'vitrina',
    'vitrina.cms',
    'vitrina.api',
    'vitrina.viisp',
    'vitrina.orgs',
    'vitrina.plans',
    'vitrina.tasks',
    'vitrina.catalogs',
    'vitrina.datasets',
    'vitrina.structure',
    'vitrina.classifiers',
    'vitrina.projects',
    'vitrina.requests',
    'vitrina.resources',
    'vitrina.comments',
    'vitrina.messages',
    'vitrina.translate',
    'vitrina.compat',
    'vitrina.likes',
]

SERIALIZATION_MODULES = {
    'xml':    'tagulous.serializers.xml_serializer',
    'json':   'tagulous.serializers.json',
    'python': 'tagulous.serializers.python',
    'yaml':   'tagulous.serializers.pyyaml',
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',

    # Django CMS
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
]

ROOT_URLCONF = 'vitrina.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',

                # Django CMS
                'sekizai.context_processors.sekizai',
                'cms.context_processors.cms_settings',

                'vitrina.context_processors.current_domain'
            ],
        },
    },
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'sass_processor.finders.CssFinder',
)

WSGI_APPLICATION = 'vitrina.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': env.db(),
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/
LANGUAGE_CODE = 'lt'
LANGUAGES = [
    ('lt', _("Lithuanian")),
    ('en', _("English")),
]

TIME_ZONE = 'Europe/Vilnius'

USE_I18N = True
USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = 'static/'

STATIC_ROOT = 'var/static/'

SASS_PROCESSOR_ROOT = STATIC_ROOT

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django-CMS
# https://docs.django-cms.org/en/latest/how_to/install.html
# https://docs.django-cms.org/en/latest/reference/configuration.html
SITE_ID = 1
X_FRAME_OPTIONS = 'SAMEORIGIN'
CMS_TEMPLATES = [
    ('pages/page.html', _("Puslapis be šoninio meniu")),
    ('pages/page_with_side_menu.html', _("Puslapis su šoniniu meniu"))
]

THUMBNAIL_HIGH_RESOLUTION = True
THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters'
)

META_USE_OG_PROPERTIES = True
META_USE_TWITTER_PROPERTIES = True
META_USE_SCHEMAORG_PROPERTIES = True
META_SITE_PROTOCOL = 'https'
META_SITE_DOMAIN = 'data.gov.lt'

PARLER_LANGUAGES = {
    None: (
        {'code': 'lt'},
        {'code': 'en'},
    ),
    1: (
        {'code': 'lt'},
        {'code': 'en'},
    ),
    'default': {
        'fallbacks': ['lt', 'en'],
    }
}
PARLER_ENABLE_CACHING = True
PARLER_CACHE_PREFIX = ''
PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = False
PARLER_DEFAULT_ACTIVATE = True

AUTH_USER_MODEL = 'vitrina_users.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Test Domain <noreply@example.com>'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

MEDIA_ROOT = BASE_DIR / 'var/media/'
MEDIA_URL = '/media/'

HAYSTACK_CONNECTIONS = {
    'default': env.search_url(),
    'test': env.search_url(var="SEARCH_URL_TEST"),
}

ELASTIC_FACET_SIZE = 50

HAYSTACK_SIGNAL_PROCESSOR = 'vitrina.datasets.search_indexes.CustomSignalProcessor'

BLOG_USE_PLACEHOLDER = False
META_USE_SITES = True

CRISPY_ALLOWED_TEMPLATE_PACKS = (
    'bulma',
)
CRISPY_TEMPLATE_PACK = 'bulma'

SYSTEM_USER_EMAIL = "system.user@example.com"

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {},
}

VITRINA_TASK_RAISE_1 = 5
VITRINA_TASK_RAISE_2 = 10
