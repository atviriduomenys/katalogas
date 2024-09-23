from django.db.models import Q
from treebeard.mp_tree import MP_NodeManager


class PublicOrganizationManager(MP_NodeManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            is_public=True,
            deleted__isnull=True,
            deleted_on__isnull=True,
        ).exclude(Q(title__isnull=True) | Q(title=""))
