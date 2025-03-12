from django.db.models.signals import post_migrate
from django.dispatch import receiver
from vitrina.classifiers.models import AreaOfManagement
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def create_default_area_of_management(sender, **kwargs):
    try:
        if sender.name == "vitrina.classifiers" and apps.is_installed(
            "vitrina.classifiers"
        ):
            AreaOfManagement.objects.exists()
            AreaOfManagement.objects.get_or_create(
                id=1, defaults={"name_lt": "Nepriskirta", "name_en": "Unassigned"}
            )
    except Exception as e:
        logger.error(
            "Failed to create default AreaOfManagement: %s", str(e), exc_info=True
        )
