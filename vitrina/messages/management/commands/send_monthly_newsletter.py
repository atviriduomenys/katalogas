from django.core.management.base import BaseCommand
from vitrina.messages.signals import send_monthly_newsletter


class Command(BaseCommand):
    help = "Send monthly newsletter to all active subscribers"

    def handle(self, *args, **options):
        result = send_monthly_newsletter.send(sender=None)
        if result:
            sent_count = result[0][1]
            self.stdout.write(self.style.SUCCESS(f"Successfully sent newsletter to {sent_count} subscribers"))
        else:
            self.stdout.write(self.style.WARNING("No newsletters sent"))
