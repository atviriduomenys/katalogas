import os
import sys

from django.apps import AppConfig


class ResourcesConfig(AppConfig):
    name = "vitrina.resources"
    label = "vitrina_resources"

    def ready(self):
        is_test = any(part in sys.argv[0] for part in ("pytest", "test", "py.test"))
        is_management_command = "manage.py" in sys.argv[0]

        if is_test or is_management_command:
            return

        if os.environ.get("RUN_MAIN", None) != "true":
            from django.conf import settings

            if "django_q" in settings.INSTALLED_APPS:
                from .schedule import setup_file_size_check_schedule

                setup_file_size_check_schedule()