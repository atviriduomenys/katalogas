from importlib import import_module


Migration = import_module(
    "djangocms_stories.migrations.0003_alter_post_options_alter_postcontent_options_and_more"
).Migration
