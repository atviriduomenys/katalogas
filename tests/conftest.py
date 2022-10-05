from functools import partial

import psycopg2
import pytest

from django.apps import apps
from django.core.management import call_command
from django.db import connection, connections
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


@pytest.fixture(scope='session', autouse=True)
def manage_unmanaged_models():
    unmanaged_models = [m for m in apps.get_models() if not m._meta.managed]
    for model in unmanaged_models:
        model._meta.managed = True
    yield
    for model in unmanaged_models:
        model._meta.managed = False


@pytest.fixture()
def app(django_app):
    yield django_app


@pytest.fixture
def csrf_exempt_django_app(django_app_factory):
    return django_app_factory(csrf_checks=False)


def _run_sql(settings, sql):
    conn = psycopg2.connect(
        dbname='postgres',
        host=settings['HOST'],
        port=settings['PORT'],
        user=settings['USER'],
        password=settings['PASSWORD'],
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()


@pytest.yield_fixture(scope='session')
def django_db_setup(django_db_blocker):
    from django.conf import settings
    test_db_name = 'test_adp_dev'
    settings.DATABASES['default']['NAME'] = test_db_name
    run_sql = partial(_run_sql, settings.DATABASES['default'])
    run_sql(f'DROP DATABASE IF EXISTS {test_db_name}')
    run_sql(f'CREATE DATABASE {test_db_name}')
    with open(settings.BASE_DB_PATH, 'r') as file:
        sqlFile = file.read()
        with django_db_blocker.unblock():
            with connection.cursor() as cursor:
                cursor.execute(sqlFile)
            call_command('migrate')
        file.close()
