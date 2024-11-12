from django.db.models.signals import post_migrate
from django.dispatch import receiver
from vitrina.classifiers.models import AreaOfManagement

@receiver(post_migrate)
def create_default_area_of_management(sender, **kwargs):
    if sender.name == 'vitrina.classifiers':
        AreaOfManagement.objects.get_or_create(
            id=1,
            defaults={'name_lt': 'Nepriskirta', 'name_en': 'Unassigned'}
        )