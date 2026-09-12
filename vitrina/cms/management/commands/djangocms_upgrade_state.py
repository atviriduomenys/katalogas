from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


LEGACY_POST_TABLE = "djangocms_blog_post"
# cms.0032 renames Title to PageContent, so a database that still has the old
# table has not been through the django-cms 3 -> 4 conversion.
LEGACY_PAGE_TABLE = "cms_title"
STORIES_DATA_MIGRATION = ("djangocms_stories", "0002_auto_20250618_1556")


def get_upgrade_state(*, tables, applied_migrations):
    # Checked first, and on its own: a django-cms 3 database also carries the
    # legacy blog tables, so without this it would read as merely "pending" -
    # refused either way, but told about the blog stage when what it lacks is
    # the whole 4.1 tool run.
    if LEGACY_PAGE_TABLE in tables:
        return "legacy_pages"

    has_legacy_data = LEGACY_POST_TABLE in tables
    stories_migrated = STORIES_DATA_MIGRATION in applied_migrations

    if has_legacy_data and stories_migrated:
        return "inconsistent"
    if has_legacy_data:
        return "pending"
    if stories_migrated:
        return "complete"
    return "fresh"


class Command(BaseCommand):
    help = "Report where the database stands in the django-cms 5 upgrade."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
        applied_migrations = set(MigrationRecorder(connection).applied_migrations())
        self.stdout.write(
            get_upgrade_state(
                tables=tables,
                applied_migrations=applied_migrations,
            )
        )
