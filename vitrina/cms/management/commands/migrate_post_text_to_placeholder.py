"""
One-time migration: move post_text HTML into a TextPlugin in the post's content placeholder.

For each PostContent with non-empty post_text the command:
  1. Inserts a TextPlugin at position 0 in the content placeholder (before existing plugins).
  2. Clears post_text.

Posts that already have placeholder plugins retain them; post_text is prepended as a new plugin.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Migrate post_text content to TextPlugin in the content placeholder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without making any changes.",
        )

    def handle(self, *args, **options):
        from cms.api import add_plugin
        from djangocms_stories.models import PostContent

        dry_run = options["dry_run"]
        # admin_manager, not objects: this has to move the text of every version,
        # and `objects` returns published content only.
        posts = PostContent.admin_manager.exclude(post_text="").exclude(post_text__isnull=True)

        # The template renders the placeholder only when the app config asks for
        # it, and falls back to post_text otherwise. Clearing post_text under a
        # config that has placeholders off would leave the article body blank.
        # A post with no app config at all falls back to post_text just the same,
        # since the template asks the config whether to use placeholders.
        disabled = sorted(
            {
                post.post.app_config.namespace if post.post.app_config else "(be konfigūracijos)"
                for post in posts
                if not (post.post.app_config and post.post.app_config.use_placeholder)
            }
        )
        if disabled:
            message = (
                "These app configs still have placeholder mode off: " + ", ".join(disabled) + ".\n"
                "Their articles are rendered from post_text, which this command clears, so turn "
                "use_placeholder on for them first - or the pages come out empty."
            )
            if not dry_run:
                raise CommandError(message)
            # A dry run is supposed to predict the real one, so say that it would
            # stop here rather than listing work that will never happen.
            self.stdout.write(self.style.WARNING(f"[dry-run] The real run would refuse: {message}"))
        self.stdout.write(f"Found {posts.count()} post(s) with post_text content.")

        for post in posts:
            self.stdout.write(f"\nPost id={post.pk} '{post.title}' (language={post.language})")
            self.stdout.write(f"  post_text length: {len(post.post_text)}")

            if dry_run:
                # Before the placeholder is read, not after: reading it creates
                # the row, and a dry run has no business writing anything.
                self.stdout.write("  [dry-run] Would create TextPlugin and clear post_text.")
                continue

            with transaction.atomic():
                plugin = add_plugin(
                    post.content,
                    "TextPlugin",
                    post.language,
                    position="first-child",
                    body=post.post_text,
                )
                post.post_text = ""
                post.save(update_fields=["post_text"])

            self.stdout.write(self.style.SUCCESS(f"  Created TextPlugin pk={plugin.pk}, cleared post_text."))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\nMigration complete."))
        else:
            self.stdout.write("\n[dry-run] No changes made.")
