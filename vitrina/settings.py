"""
Django settings for vitrina project.

Generated by 'django-admin startproject' using Django 4.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
import environ
from pathlib import Path

from django.contrib import messages
from django.utils.translation import gettext_lazy as _


env = environ.Env()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(env.path(
    'VITRINA_BASE_PATH',
    default=Path(__file__).resolve().parent.parent,
))

# Take environment variables from .env file
environ.Env.read_env(BASE_DIR / '.env')

BASE_DB_PATH = BASE_DIR / 'resources/adp-pg.sql'
LOCALE_PATHS = [
    env.path('VITRINA_LOCALE_PATH', default=BASE_DIR / 'vitrina/locale/'),
]
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default=(
    'django-insecure-((hv!%qj6+p@)vnuy6%(@l#0m=n*o@dy3sn3sop0m$!49^*xvy'
))

VIISP_AUTHORIZE_URL = env('VIISP_AUTHORIZE_URL')
VIISP_PROXY_AUTH = env('VIISP_PROXY_AUTH')
VIISP_PID = env('VIISP_PID')

SPINTA_EXECUTABLE = BASE_DIR / env('SPINTA_EXECUTABLE')
SPINTA_SERVER_URL = env('SPINTA_SERVER_URL')
SPINTA_SERVER_NAME = env('SPINTA_SERVER_NAME')
SPINTA_PATH = BASE_DIR / env('SPINTA_PATH')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = (
    ['localhost', '127.0.0.1'] +
    env.list('ALLOWED_HOSTS', default=[])
)

# If runing behind proxy, set this to HTTP_X_FORWARDED_PROTO
_SECURE_PROXY_SSL_HEADER = env.str(
    'DJANGO_SECURE_PROXY_SSL_HEADER',
    default=None,
)
if _SECURE_PROXY_SSL_HEADER:
    SECURE_PROXY_SSL_HEADER = (_SECURE_PROXY_SSL_HEADER, "https")

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
    'django.contrib.humanize',
    'extra_settings',
    'rest_framework',
    'drf_yasg',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'vitrina.users',

    # Django CMS
    'django_otp',
    'django_otp.plugins.otp_email',
    'sass_processor',
    'sekizai',
    'cms',
    'menus',
    'treebeard',
    'filer',
    'easy_thumbnails',
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
    'django_select2',
    'django_recaptcha',
    'vitrina',
    'vitrina.cms',
    'vitrina.api',
    'vitrina.viisp',
    'vitrina.orgs',
    'vitrina.plans',
    'vitrina.tasks',
    'vitrina.catalogs',
    'vitrina.datasets',
    'vitrina.statistics',
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
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'vitrina.middleware.NoAutoLocaleMiddleware',
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
        'DIRS': [os.path.join(BASE_DIR, 'templates'),
                 os.path.join(BASE_DIR, 'vitrina', 'templates', 'allauth')],
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

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
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
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'vitrina.validators.UppercaseValidator',
    },
    {
        'NAME': 'vitrina.validators.LowercaseValidator',
    },
    {
        'NAME': 'vitrina.validators.DigitValidator',
    },
    {
        'NAME': 'vitrina.validators.SpecialCharacterValidator',
    },
    {
        'NAME': 'vitrina.validators.UniquePasswordValidator',
    },
    {
        'NAME': 'vitrina.validators.ZxcvbnPasswordValidator',
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


MEDIA_URL = 'media/'
MEDIA_ROOT = env.path('MEDIA_ROOT', default=BASE_DIR / 'var/media/')

STATIC_URL = 'static/'
STATIC_ROOT = env.path('STATIC_ROOT', default=BASE_DIR / 'var/static/')

SASS_PROCESSOR_ROOT = STATIC_ROOT

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django-CMS
# https://docs.django-cms.org/en/latest/how_to/install.html
# https://docs.django-cms.org/en/latest/reference/configuration.html
SITE_ID = 1

# Provider specific settings
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_PROVIDERS = {
    'viisp': {
        'SCOPE': [
            'first_name',
            'last_name',
            'email'
        ],
        'FIELDS': [
            'first_name',
            'last_name',
            'email'
        ],
        'VERIFIED_EMAIL': True
    }
}
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'

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
THUMBNAIL_ALIASES = {
    '': {
        'list': {'size': (480, 320)},
    },
}

FILER_ADD_FILE_VALIDATORS = {
    "text/html": ["filer.validation.deny_html"],
    "image/svg+xml": ["filer.validation.deny"],
    "text/javascript": ["filer.validation.deny"],
    "application/javascript": ["filer.validation.deny"],
    "application/x-msdownload": ["filer.validation.deny"],
    "application/x-sh": ["filer.validation.deny"],
    "application/x-httpd-php": ["filer.validation.deny"],
    "application/octet-stream": ["filer.validation.deny"],
}

META_USE_OG_PROPERTIES = True
META_USE_TWITTER_PROPERTIES = True
META_USE_SCHEMAORG_PROPERTIES = True
META_SITE_PROTOCOL = 'https'
META_SITE_DOMAIN = 'data.gov.lt'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "allauth.socialaccount.context_processors.socialaccount",
)

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

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Test Domain <noreply@example.com>')
email = env.email('EMAIL_URL', default='consolemail://')
EMAIL_BACKEND = email['EMAIL_BACKEND']
EMAIL_HOST = email['EMAIL_HOST']
EMAIL_PORT = email['EMAIL_PORT']
EMAIL_HOST_USER = email['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = email['EMAIL_HOST_PASSWORD']
EMAIL_FILE_PATH = email['EMAIL_FILE_PATH']
EMAIL_USE_TLS = email.get('EMAIL_USE_TLS')

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

HASHER_SALT = "2LxpaW5qOe80xZjTPyzpgi"

_search_url = env.search_url()
_search_url['ENGINE'] = 'vitrina.datasets.search_backends.ElasticSearchEngine'
_search_url_test = env.str(var="SEARCH_URL_TEST", default='')
if _search_url_test:
    _search_url_test = env.search_url(var="SEARCH_URL_TEST")
else:
    _search_url_test = {**_search_url, 'INDEX_NAME': 'test'}
HAYSTACK_CONNECTIONS = {
    'default': _search_url,
    'test': _search_url_test,
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

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_SIGNUP_REDIRECT_URL = 'password-set'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
CORS_ALLOWED_ORIGINS = ['https://test.epaslaugos.lt']
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECT = False

TRANSLATION_CLIENT_ID = env('TRANSLATION_CLIENT_ID', default='')
SPINTA_SERVER_URL = env('SPINTA_SERVER_URL', default='https://get-test.data.gov.lt')
SPINTA_SERVER_CLIENT_ID = env('SPINTA_SERVER_CLIENT_ID', default='')
SPINTA_SERVER_CLIENT_SECRET = env('SPINTA_SERVER_CLIENT_SECRET', default='')

SECURE_HSTS_SECONDS = 31536000 # The max-age must be at least 31536000 seconds (1 year)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

RECAPTCHA_PUBLIC_KEY = env('RECAPTCHA_PUBLIC_KEY', default='')
RECAPTCHA_PRIVATE_KEY = env('RECAPTCHA_PRIVATE_KEY', default='')

MESSAGE_TAGS = {
    messages.DEBUG: 'is-light',
    messages.INFO: 'is-info',
    messages.SUCCESS: 'is-success',
    messages.WARNING: 'is-warning',
    messages.ERROR: 'is-danger',
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

DATA_UPLOAD_MAX_MEMORY_SIZE = None

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True

OTP_EMAIL_TOKEN_VALIDITY = 600
