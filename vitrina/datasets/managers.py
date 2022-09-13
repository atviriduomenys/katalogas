from django.db import models


class PublicDatasetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()

    def get_from_url_args(self, **kwargs):
        return self.get(organization__kind=kwargs.get('org_kind'),
                        organization__slug=kwargs.get('org_slug'),
                        slug=kwargs.get('slug'))
