from django.core.management.base import BaseCommand
from vitrina.requests.models import Request
import argostranslate.package
import argostranslate.translate


class Command(BaseCommand):
    help = "Translate Request titles and descriptions from Lithuanian to English."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be translated without actually saving",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of requests to translate",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=True,
            help="Skip requests that already have English translations",
        )

    def handle(self, *args, **options):
        self.stdout.write("Setting up translation...")

        # Check if Lithuanian -> English is already installed
        installed_languages = argostranslate.translate.get_installed_languages()
        lt_installed = any(lang.code == "lt" for lang in installed_languages)
        en_installed = any(lang.code == "en" for lang in installed_languages)

        if not (lt_installed and en_installed):
            self.stdout.write("Downloading Lithuanian->English translation package (first time only)...")

            # Update package index
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()

            # Find Lithuanian -> English package
            lt_en_package = next(filter(lambda x: x.from_code == "lt" and x.to_code == "en", available_packages), None)

            if not lt_en_package:
                self.stdout.write(self.style.ERROR("Lithuanian->English package not found"))
                return

            # Download and install
            download_path = lt_en_package.download()
            argostranslate.package.install_from_path(download_path)
            self.stdout.write(self.style.SUCCESS("Package installed!"))
        else:
            self.stdout.write(self.style.SUCCESS("Translation package already installed"))

        # Get translation model
        RequestTranslation = Request._parler_meta.root_model

        # Get requests
        requests = Request.objects.all()
        if options["limit"]:
            requests = requests[: options["limit"]]

        translated_count = 0
        skipped_count = 0
        error_count = 0

        total = requests.count()
        self.stdout.write(f"\nProcessing {total} requests...\n")

        for idx, req in enumerate(requests, 1):
            try:
                # Check if English translation exists in database
                en_translation_exists = RequestTranslation.objects.filter(master_id=req.pk, language_code="en").exists()

                if options["skip_existing"] and en_translation_exists:
                    self.stdout.write(f"[{idx}/{total}] Skipping #{req.pk} - English exists")
                    skipped_count += 1
                    continue

                # Get Lithuanian content
                req.set_current_language("lt")
                lt_title = req.title or ""
                lt_description = req.description or ""

                if not lt_title and not lt_description:
                    self.stdout.write(f"[{idx}/{total}] Skipping #{req.pk} - No Lithuanian content")
                    skipped_count += 1
                    continue

                # Translate
                en_title = ""
                en_description = ""

                if lt_title:
                    en_title = argostranslate.translate.translate(lt_title, "lt", "en")

                if lt_description:
                    en_description = argostranslate.translate.translate(lt_description, "lt", "en")

                # Show preview
                self.stdout.write(f"\n[{idx}/{total}] Request #{req.pk}:")
                self.stdout.write(f"  LT: {lt_title[:70]}...")
                self.stdout.write(f"  EN: {en_title[:70]}...")

                # Save if not dry run
                if not options["dry_run"]:
                    req.set_current_language("en")
                    req.title = en_title
                    req.description = en_description
                    req.save()

                translated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{idx}/{total}] Error with #{req.pk}: {e}"))
                error_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"DRY RUN - Would translate: {translated_count}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Translated: {translated_count}"))

        self.stdout.write(f"Skipped: {skipped_count}")
        if error_count:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))
