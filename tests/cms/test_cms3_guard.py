"""migrate refuses a django-cms 3 database, long after the upgrade itself.

A backup from before the upgrade, restored into an environment already on
django-cms 5, would otherwise be migrated past the point of no return by the
next start or by a migrate run by hand.
"""

import pytest
from django.core.management.base import CommandError
from django.db.models.signals import pre_migrate

from vitrina.cms import apps as cms_apps


class FakeConnection:
    def __init__(self, tables):
        self.introspection = self
        self._tables = tables

    def table_names(self, cursor=None):
        return list(self._tables)


def test_a_cms3_database_is_refused(monkeypatch):
    monkeypatch.setattr(cms_apps, "connections", {"default": FakeConnection({"cms_page", "cms_title"})})

    with pytest.raises(CommandError, match="cms_title"):
        cms_apps._refuse_cms3_schema(sender=None, using="default")


def test_a_cms5_database_passes(monkeypatch):
    monkeypatch.setattr(cms_apps, "connections", {"default": FakeConnection({"cms_page", "cms_pagecontent"})})

    cms_apps._refuse_cms3_schema(sender=None, using="default")


def test_the_guard_is_wired_to_migrate():
    """pre_migrate fires before any migration is applied - which is the whole point."""
    uids = {key[0] for key, *_ in pre_migrate.receivers}

    assert "vitrina_cms.refuse_cms3_schema" in uids
