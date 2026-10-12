from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver

from vitrina.uapi.models import AgentEnvironment


@receiver(pre_save, sender=AgentEnvironment)
def keep_uri(sender: type[AgentEnvironment], instance: AgentEnvironment, **kwargs: Any) -> None:
    """Keep the stored `uri` on every save, raw ones included.

    The agent checks the `aud` claim against this value, so it must never change. Reverting a django-reversion
    version bypasses `Model.save()`, and a version saved before the field existed would otherwise bring a
    freshly generated default.
    """
    stored_uri = sender._base_manager.filter(pk=instance.pk).values_list("uri", flat=True).first()
    if stored_uri:
        instance.uri = stored_uri
