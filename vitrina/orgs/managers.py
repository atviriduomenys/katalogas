from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Manager
from treebeard.mp_tree import MP_NodeManager
from django.apps import apps


class PublicOrganizationManager(MP_NodeManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            is_public=True,
            deleted__isnull=True,
            deleted_on__isnull=True,
        ).exclude(Q(title__isnull=True) | Q(title=""))


class OrganizationRepresentativeManager(Manager):
    def get_queryset(self):
        Organization = apps.get_model('vitrina_orgs', 'Organization')
        return super().get_queryset().filter(
            content_type=ContentType.objects.get_for_model(Organization),
            deleted__isnull=True,
            deleted_on__isnull=True,
        )


class OrganizationRepresentativeWithDeletedManager(Manager):
    def get_queryset(self):
        Organization = apps.get_model('vitrina_orgs', 'Organization')
        return super().get_queryset().filter(
            content_type=ContentType.objects.get_for_model(Organization)
        )


class RepresentativeManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            deleted__isnull=True,
            deleted_on__isnull=True,
        )


class RepresentativeWithDeletedManager(Manager):
    pass
