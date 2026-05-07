from django.core.management.commands.makemessages import Command as BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options) -> None:
        if not options.get("locale"):
            options["locale"] = ["en", "lt"]
        if not options.get("no_location"):
            options["no_location"] = True
        super().handle(*args, **options)
