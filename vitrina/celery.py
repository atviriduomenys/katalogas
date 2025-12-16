import os
import inspect
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
    - Propagates a `user_id` (if provided) into task message headers for downstream use.
    - Wraps task execution in a Reversion revision, attaching the user (when resolvable)
      and a structured JSON comment describing the task call.
    """
    abstract = True

    def apply_async(self, args: Any | None = None, kwargs: Any | None = None, **options) -> Any:
        """Enqueue the task, optionally embedding `user_id` into message headers.

        If the task's `run()` accepts `user_id` (explicitly or via `**kwargs`),
        the kwarg is left intact. Otherwise it is removed from kwargs to avoid
        unexpected-kwarg errors, while still being forwarded via headers.
        """
        kwargs = kwargs or {}
        if self._accepts_kwarg("user_id"):
            user_id = kwargs.get("user_id")
        else:
            user_id = kwargs.pop("user_id", None)

        headers = options.pop("headers", {})
        if user_id:
            headers = {**headers, "user_id": user_id}

        return super().apply_async(args=args, kwargs=kwargs, headers=headers, **options)

    def __call__(self, *args, **kwargs) -> Any:
        """Execute the task inside a Reversion revision.

        Tries to read `user_id` from Celery request headers, resolves it to a Django user,
        and sets Reversion's user accordingly. Always writes a JSON comment describing
        the invocation (task name + args/kwargs).
        """
        with reversion.create_revision():
            request = getattr(self, "request", None)
            user_id = None
            if request:
                headers = getattr(request, "headers", {}) or {}
                user_id = headers.get("user_id")

            if user_id:
                User = get_user_model()
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    user = None

                if user:
                    reversion.set_user(user)

            comment = RevisionComment(
                source=RevisionSource.TASK,
                action=self.name,
                args=list(args),
                kwargs=kwargs,
            )
            reversion.set_comment(comment.to_json())
            return super().__call__(*args, **kwargs)

    def _accepts_kwarg(self, kwarg_name: str) -> bool:
        """Return True if `run()` accepts the given kwarg (directly or via `**kwargs`)."""
        signature = inspect.signature(self.run)
        for parameter in signature.parameters.values():
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == kwarg_name:
                return True
        return False


app.Task = RevisionedTask
app.autodiscover_tasks()
