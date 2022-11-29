from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.api.factories import APIKeyFactory
from vitrina.catalogs.factories import CatalogFactory
from vitrina.classifiers.factories import CategoryFactory, LicenceFactory


@pytest.mark.django_db
def test_retrieve_catalog_list_without_api_key(app: DjangoTestApp):
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_catalog_list_with_disabled_api_key(app: DjangoTestApp):
    api_key = APIKeyFactory(enabled=False)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_catalog_list_with_expired_api_key(app: DjangoTestApp):
    api_key = APIKeyFactory(expires=datetime(2000, 12, 24))
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_catalog_list_with_correct_api_key(app: DjangoTestApp):
    catalog = CatalogFactory()
    api_key = APIKeyFactory()
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-catalog-list"), expect_errors=True)
    assert res.json == [{
        'description': catalog.description,
        'id': str(catalog.identifier),
        'licence': {
            'description': catalog.licence.description,
            'id': str(catalog.licence.identifier),
            'title': catalog.licence.title
        },
        'title': catalog.title
    }]


@pytest.mark.django_db
def test_retrieve_category_list_without_api_key(app: DjangoTestApp):
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_category_list_with_disabled_api_key(app: DjangoTestApp):
    api_key = APIKeyFactory(enabled=False)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_category_list_with_expired_api_key(app: DjangoTestApp):
    api_key = APIKeyFactory(expires=datetime(2000, 12, 24))
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_category_list_with_correct_api_key(app: DjangoTestApp):
    category = CategoryFactory()
    api_key = APIKeyFactory()
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-category-list"), expect_errors=True)
    assert res.json == [{
        'description': category.description,
        'id': str(category.pk),
        'title': category.title
    }]


@pytest.mark.django_db
def test_retrieve_licence_list_without_api_key(app: DjangoTestApp):
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_licence_licence_list_with_disabled_api_key(app: DjangoTestApp):
    api_key = APIKeyFactory(enabled=False)
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_licence_licence_list_with_expired_api_key(app: DjangoTestApp):
    api_key = APIKeyFactory(expires=datetime(2000, 12, 24))
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.status_code == 403


@pytest.mark.django_db
def test_retrieve_licence_list_with_correct_api_key(app: DjangoTestApp):
    licence = LicenceFactory()
    api_key = APIKeyFactory()
    app.extra_environ.update({
        'HTTP_AUTHORIZATION': f'ApiKey {api_key.api_key}'
    })
    res = app.get(reverse("api-licence-list"), expect_errors=True)
    assert res.json == [{
        'description': licence.description,
        'id': str(licence.identifier),
        'title': licence.title
    }]
