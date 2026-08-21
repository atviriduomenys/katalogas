from django.core.management.base import BaseCommand

from vitrina.search.indexing import rebuild


class Command(BaseCommand):
    help = "Rebuild the search data of every dataset and request."

    def handle(self, *args, **options):
        rebuild(stdout=self.stdout)
