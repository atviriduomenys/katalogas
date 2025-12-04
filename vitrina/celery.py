import os
import inspect

from celery import Celery, Task
import reversion
from django.contrib.auth import get_user_model
from vitrina.utils import RevisionComment, RevisionSource

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
app = Celery("vitrina")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.timezone = "UTC"

class RevisionedTask(Task):
    def apply_async(self, args=None, kwargs=None, **options):
        kwargs = kwargs or {}

        user_id = kwargs.pop("user_id", None)

        headers = options.pop("headers", {}) or {}
        if user_id:
            headers = {**headers, "user_id": user_id}

        return super().apply_async(args=args, kwargs=kwargs, headers=headers, **options)
    
    def __call__(self, *args, **kwargs):
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
                view=self.name,
                args=list(args),
                kwargs=kwargs,
            )
            reversion.set_comment(comment.to_json())
            return super().__call__(*args, **kwargs)
        
    def _accepts_kwarg(self, kwarg_name: str) -> bool:
        """
        Return True if self.run accepts kwarg_name or **kwargs.
        """
        signature = inspect.signature(self.run)
        for parameter in signature.parameters.values():
            # If function has **kwargs – it will accept any kwarg
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            # Explicit kwarg name
            if parameter.name == kwarg_name:
                return True
        return False
        
app.task_cls = RevisionedTask
