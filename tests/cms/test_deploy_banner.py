from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from djangocms_text_ckeditor.fields import HTMLFormField

from vitrina.cms.forms import DeploymentAdminForm
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
    return Template(
        "{% load util_tags %}{% get_deploy_banner as banner %}{% if banner %}{{ banner.pk }}{% else %}none{% endif %}"
    ).render(Context())


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


class DeploymentAdminFormTest(TestCase):
    def test_message_fields_use_ckeditor(self):
        form = DeploymentAdminForm()
        self.assertIsInstance(form.fields["message_lt"], HTMLFormField)
        self.assertIsInstance(form.fields["message_en"], HTMLFormField)

    def test_form_exposes_new_fields(self):
        form = DeploymentAdminForm()
        for name in ("level", "is_published", "start_date", "end_date", "message_lt", "message_en"):
            self.assertIn(name, form.fields)

    def test_message_en_optional(self):
        form = DeploymentAdminForm()
        self.assertFalse(form.fields["message_en"].required)

    def test_form_edits_existing_instance(self):
        deployment = Deployment.objects.create(message_lt="Originalus tekstas", is_published=True, **_window())
        form = DeploymentAdminForm(instance=deployment)
        self.assertEqual(form.initial["message_lt"], "Originalus tekstas")


class DeployBannerTemplateTest(TestCase):
    def test_link_is_not_escaped(self):
        Deployment.objects.create(
            message_lt='Skaitykite <a href="https://data.gov.lt">čia</a>',
            is_published=True,
            **_window(),
        )
        html = render_to_string("component/deploy_banner.html")
        self.assertIn('<a href="https://data.gov.lt">čia</a>', html)
        self.assertNotIn("&lt;a href", html)

    def test_info_level_styling(self):
        Deployment.objects.create(message_lt="Info", level="info", is_published=True, **_window())
        html = render_to_string("component/deploy_banner.html")
        self.assertIn("is-info", html)
        self.assertIn("fa-info-circle", html)

    def test_warning_level_styling(self):
        Deployment.objects.create(message_lt="Warn", level="warning", is_published=True, **_window())
        html = render_to_string("component/deploy_banner.html")
        self.assertIn("is-warning", html)
        self.assertIn("fa-exclamation-triangle", html)

    def test_critical_level_styling(self):
        Deployment.objects.create(message_lt="Crit", level="critical", is_published=True, **_window())
        html = render_to_string("component/deploy_banner.html")
        self.assertIn("is-danger", html)
        self.assertIn("fa-exclamation-circle", html)

    def test_no_banner_when_none_published(self):
        Deployment.objects.create(message_lt="Draft", is_published=False, **_window())
        html = render_to_string("component/deploy_banner.html")
        self.assertNotIn("notification", html)
