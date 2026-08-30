from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


LEGACY_POST_TABLE = "djangocms_blog_post"
STORIES_DATA_MIGRATION = ("djangocms_stories", "0002_auto_20250618_1556")


def get_upgrade_state(*, tables, applied_migrations):
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
    help = "Report whether the one-time djangocms-blog data migration is needed."

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
