from unittest.mock import patch

import pytest

from django.core import mail
from django.urls import reverse

from vitrina.messages.factories import MassMailFactory
from vitrina.messages.tasks import send_mass_mail, send_mass_mail_batch


@pytest.mark.django_db
class TestMassMailAdmin:
    def test_does_not_send_if_send_is_false(self, app, admin_user):
        mass_mail = MassMailFactory(send=False)
        app.set_user(admin_user)

        form = app.get(reverse("admin:vitrina_messages_massmail_change", args=[mass_mail.pk])).forms["massmail_form"]

        with patch("vitrina.messages.admin.send_mass_mail.delay") as mock_delay:
            response = form.submit()

        assert response.status_code == 302
        mock_delay.assert_not_called()
        assert len(mail.outbox) == 0

    def test_does_not_send_if_send_was_not_changed(self, app, admin_user):
        mass_mail = MassMailFactory(send=True)
        app.set_user(admin_user)

        form = app.get(reverse("admin:vitrina_messages_massmail_change", args=[mass_mail.pk])).forms["massmail_form"]

        with patch("vitrina.messages.admin.send_mass_mail.delay") as mock_delay:
            response = form.submit()

        assert response.status_code == 302
        mock_delay.assert_not_called()
        assert len(mail.outbox) == 0

    def test_sends_emails_when_send_is_changed_to_true(self, app, admin_user, django_capture_on_commit_callbacks):
        mass_mail = MassMailFactory(send=False, recipients="test@example.com")
        app.set_user(admin_user)

        form = app.get(reverse("admin:vitrina_messages_massmail_change", args=[mass_mail.pk])).forms["massmail_form"]
        form["send"] = True

        with patch("vitrina.messages.admin.send_mass_mail.delay") as mock_delay:
            with django_capture_on_commit_callbacks(execute=False) as callbacks:
                response = form.submit()

            assert response.status_code == 302
            assert len(callbacks) == 1

            callbacks[0]()
            mock_delay.assert_called_once_with(mass_mail.pk)

    @pytest.mark.parametrize(
        ("recipient_count", "expected_batches"),
        [
            (3, [3]),
            (51, [50, 1]),
        ],
    )
    def test_sends_emails_in_batches(
        self, app, admin_user, django_capture_on_commit_callbacks, recipient_count, expected_batches
    ):
        recipients = [f"test{i}@example.com" for i in range(recipient_count)]
        mass_mail = MassMailFactory(send=False, recipients=", ".join(recipients))
        app.set_user(admin_user)

        form = app.get(reverse("admin:vitrina_messages_massmail_change", args=[mass_mail.pk])).forms["massmail_form"]
        form["send"] = True

        with (
            patch(
                "vitrina.messages.admin.send_mass_mail.delay",
                side_effect=lambda pk: send_mass_mail(pk),
            ) as mock_delay,
            patch(
                "vitrina.messages.tasks.send_mass_mail_batch.delay",
                side_effect=lambda pk, batch: send_mass_mail_batch.apply(args=(pk, batch)).get(),
            ),
        ):
            with django_capture_on_commit_callbacks(execute=False) as callbacks:
                response = form.submit()

            assert len(callbacks) == 1
            callbacks[0]()

            mock_delay.assert_called_once_with(mass_mail.pk)

        assert response.status_code == 302
        assert [len(message.bcc) for message in mail.outbox] == expected_batches
        assert sorted(email for message in mail.outbox for email in message.bcc) == sorted(recipients)
