from django.db import models


class PublicCommentManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(
            is_public=True,
        )
