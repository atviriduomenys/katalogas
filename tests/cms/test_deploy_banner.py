from django.template import Context, Template
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from vitrina.cms.models import Deployment


def _window():
    now = timezone.now()
    return {"start_date": now - timedelta(days=1), "end_date": now + timedelta(days=1)}


class DeploymentModelTest(TestCase):
    def test_level_defaults_to_info(self):
        deployment = Deployment.objects.create(message_lt="Labas", **_window())
        self.assertEqual(deployment.level, Deployment.DeploymentLevel.INFO)

    def test_is_published_defaults_to_false(self):
        deployment = Deployment.objects.create(message_lt="Labas", **_window())
        self.assertFalse(deployment.is_published)

    def test_publishing_unpublishes_others(self):
        first = Deployment.objects.create(message_lt="Senas", is_published=True, **_window())
        second = Deployment.objects.create(message_lt="Naujas", is_published=True, **_window())

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_published)
        self.assertTrue(second.is_published)

    def test_saving_unpublished_leaves_others_alone(self):
        published = Deployment.objects.create(message_lt="Rodomas", is_published=True, **_window())
        Deployment.objects.create(message_lt="Juodrastis", is_published=False, **_window())

        published.refresh_from_db()
        self.assertTrue(published.is_published)


def _render_tag():
    return Template("{% load util_tags %}{% get_deploy_banner as banner %}{{ banner.pk|default:'none' }}").render(
        Context()
    )


class GetDeployBannerTest(TestCase):
    def test_returns_published_row_not_first(self):
        Deployment.objects.create(message_lt="Senas juodrastis", is_published=False, **_window())
        published = Deployment.objects.create(message_lt="Publikuotas", is_published=True, **_window())

        self.assertEqual(_render_tag(), str(published.pk))

    def test_returns_none_when_nothing_published(self):
        Deployment.objects.create(message_lt="Juodrastis", is_published=False, **_window())
        self.assertEqual(_render_tag(), "none")

    def test_published_but_outside_window_returns_none(self):
        now = timezone.now()
        Deployment.objects.create(
            message_lt="Praeitis",
            is_published=True,
            start_date=now - timedelta(days=5),
            end_date=now - timedelta(days=3),
        )
        self.assertEqual(_render_tag(), "none")
