import os

from celery import Celery
import reversion

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
app = Celery("vitrina")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.timezone = "UTC"


class RevisionedTask(app.Task):
    def __call__(self, *args, **kwargs):
        with reversion.create_revision():
            return super().__call__(*args, **kwargs)


app.Task = RevisionedTask
app.autodiscover_tasks()
