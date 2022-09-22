from importlib import import_module

import pytest
from django.apps import apps
from django.db import connection
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import CategoryFactory
from vitrina.classifiers.models import Category

data_migration = import_module('vitrina.classifiers.migrations.0005_auto_20220919_1047')


def reset_mp_fields(category):
    category.path = ''
    category.depth = ''
    category. numchild = ''
    return category


@pytest.fixture
def categories():
    category = Category.objects.create(version=1, featured=False, depth=0, path='1')
    category1 = Category.objects.create(version=1, featured=False, parent=category, depth=0, path='2')
    category2 = Category.objects.create(version=1, featured=False, parent=category1, depth=0, path='3')
    category3 = Category.objects.create(version=1, featured=False, parent=category1, depth=0, path='4')


@pytest.mark.django_db
def test_mp_bad_field_data(app: DjangoTestApp, categories):
    cats = Category.objects.all()
    assert cats[0].path == '1'
    assert cats[1].path == '2'
    assert cats[2].path == '3'
    assert cats[3].path == '4'


@pytest.mark.django_db
def test_root_data_set(app: DjangoTestApp, categories):
    root_cats = Category.objects.filter(parent__isnull=True)
    data_migration.set_root_category_data(root_cats, Category)

    assert root_cats[0].depth == 0
    assert root_cats[0].numchild == 1


@pytest.mark.django_db
def test_child_data_set(app: DjangoTestApp, categories):
    child_cats = Category.objects.filter(parent__isnull=False)
    data_migration.set_child_category_data(child_cats, Category)

    assert child_cats[0].depth == 1
    assert child_cats[0].numchild == 2
    assert child_cats[1].depth == 2
    assert child_cats[1].numchild == 0
    assert child_cats[2].depth == 2
    assert child_cats[2].numchild == 0


@pytest.mark.django_db
def test_path_generation(app: DjangoTestApp, categories):
    cats = Category.objects.all()
    data_migration.calculate_category_paths(Category)

    assert cats[0].path == '0000'
    assert cats[1].path == '00000001'
    assert cats[2].path == '000000010002'
    assert cats[3].path == '000000010003'


