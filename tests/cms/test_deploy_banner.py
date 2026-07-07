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
