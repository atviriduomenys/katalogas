from celery import shared_task
from django.core.mail import get_connection, EmailMultiAlternatives
from django.utils.html import strip_tags

from vitrina import settings
from vitrina.helpers import logger
from vitrina.messages.models import MassMail, SentMail


@shared_task
def send_mass_mail(mass_mail_id: int) -> None:
    mail = MassMail.objects.filter(pk=mass_mail_id).first()
    if not mail:
        return

    recipients = [recipient.strip() for recipient in mail.recipients.split(",") if recipient.strip()]
    batch_size = 50

    for i in range(0, len(recipients), batch_size):
        batch = recipients[i : i + batch_size]

        send_mass_mail_batch.delay(mass_mail_id, batch)


@shared_task(
    bind=True,
    max_retries=5,
    rate_limit="6/m",
)
def send_mass_mail_batch(self, mass_mail_id: int, batch: list) -> None:
    mail = MassMail.objects.filter(pk=mass_mail_id).first()

    if not mail:
        return

    connection = get_connection()
    email_send = False

    try:
        email = EmailMultiAlternatives(
            subject=mail.email_subject,
            body=strip_tags(mail.email_content),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[],
            bcc=batch,
            connection=connection,
        )
        email.attach_alternative(mail.email_content, "text/html")
        email_send = email.send() > 0

    except Exception as e:
        if self.request.retries < self.max_retries:
            countdown = min(60, 5 * (2**self.request.retries))

            raise self.retry(exc=e, countdown=countdown)

        logger.exception(
            "Email batch failed: recipients=%s",
            batch,
        )

    finally:
        connection.close()

    SentMail.objects.create(
        deleted=None,
        deleted_on=None,
        version=0,
        recipient=batch,
        email_subject=mail.email_subject,
        email_content=mail.email_content,
        email_sent=email_send,
    )
