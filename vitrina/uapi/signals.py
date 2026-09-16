from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver

from vitrina.uapi.models import AgentEnvironment


@receiver(pre_save, sender=AgentEnvironment)
def keep_instance_uri(sender: type[AgentEnvironment], instance: AgentEnvironment, **kwargs: Any) -> None:
    """Keep the stored `instance_uri` on every save, raw ones included.

    Spinta checks the `aud` claim against this value, so it must never change. Reverting a django-reversion
    version bypasses `Model.save()`, and a version saved before the field existed would otherwise bring a
    freshly generated default.
    """
    stored_instance_uri = sender._base_manager.filter(pk=instance.pk).values_list("instance_uri", flat=True).first()
    if stored_instance_uri:
        instance.instance_uri = stored_instance_uri
