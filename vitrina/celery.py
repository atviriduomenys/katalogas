import os
from typing import Any

from celery import Celery
import reversion
from django.contrib.auth import get_user_model
from vitrina.utils import RevisionComment, RevisionSource

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
app = Celery("vitrina")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.timezone = "UTC"


class RevisionedTask(app.Task):
    """Celery task base class that records Django Reversion revisions for each run.

    Responsibilities:
    - Propagates a `_reversion_user_id` (if provided) into task message headers for downstream use.
    - Wraps task execution in a Reversion revision, attaching the user (when resolvable)
      and a structured JSON comment describing the task call.
    """

    abstract = True

    def apply_async(self, args: Any = None, kwargs: Any = None, **options) -> Any:
        """Enqueue the task, optionally embedding `_reversion_user_id` into message headers."""
        kwargs = kwargs or {}

        headers = options.pop("headers", {})
        if user_id := kwargs.pop("_reversion_user_id", None):
            headers = {**headers, "_reversion_user_id": user_id}

        return super().apply_async(args=args, kwargs=kwargs, headers=headers, **options)

    def __call__(self, *args, **kwargs) -> Any:
        """Execute the task inside a Reversion revision.

        Tries to read `_reversion_user_id` from Celery request headers, resolves it to a Django user,
        and sets Reversion's user accordingly. Always writes a JSON comment describing
        the invocation (task name + args/kwargs).
        """
        with reversion.create_revision():
            headers = {}
            if request := getattr(self, "request", None):
                headers = getattr(request, "headers", {}) or {}

            if user_id := headers.get("_reversion_user_id"):
                User = get_user_model()
                try:
                    user = User.objects.get(pk=user_id)
                    reversion.set_user(user)
                except User.DoesNotExist:
                    pass

            comment = RevisionComment(
                source=RevisionSource.TASK,
                action=self.name,
                args=list(args),
                kwargs=kwargs,
            )
            reversion.set_comment(comment.to_json())
            return super().__call__(*args, **kwargs)


app.Task = RevisionedTask
app.autodiscover_tasks()
