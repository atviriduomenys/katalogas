from importlib import import_module

from vitrina.cms.management.commands.djangocms_upgrade_state import get_upgrade_state


def test_upgrade_is_pending_while_legacy_blog_data_has_not_been_migrated():
    state = get_upgrade_state(
        tables={"djangocms_blog_post"},
        applied_migrations=set(),
    )

    assert state == "pending"


def test_upgrade_is_complete_after_stories_data_migration():
    state = get_upgrade_state(
        tables=set(),
        applied_migrations={("djangocms_stories", "0002_auto_20250618_1556")},
    )

    assert state == "complete"


def test_fresh_database_does_not_need_the_legacy_migration_stage():
    state = get_upgrade_state(tables=set(), applied_migrations=set())

    assert state == "fresh"


def test_upgrade_is_inconsistent_if_legacy_tables_remain_after_migration():
    state = get_upgrade_state(
        tables={"djangocms_blog_post"},
        applied_migrations={("djangocms_stories", "0002_auto_20250618_1556")},
    )

    assert state == "inconsistent"


def test_custom_stories_data_migration_runs_after_file_resources_exist():
    migration = import_module("vitrina.cms.stories_migrations.0002_auto_20250618_1556").Migration

    assert ("vitrina_cms", "0006_deployment_is_published_deployment_level") in migration.dependencies


def test_mirrored_stories_migrations_match_the_installed_package():
    """MIGRATION_MODULES replaces the app's migrations with the copies here.

    Django then loads only these, so a migration added by a djangocms-stories
    release would be skipped silently and its column would simply never appear.
    """
    from pathlib import Path

    import djangocms_stories.migrations as upstream

    import vitrina.cms.stories_migrations as mirrored

    def names(module):
        return {path.stem for path in Path(module.__file__).parent.glob("0*.py")}

    assert names(mirrored) == names(upstream)
