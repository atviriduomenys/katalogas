from importlib import import_module


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
