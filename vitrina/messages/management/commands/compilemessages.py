from django.core.management.commands.compilemessages import Command as BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options) -> None:
        if not options.get("locale"):
            options["locale"] = ["en", "lt"]
        super().handle(*args, **options)
