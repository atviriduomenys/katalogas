from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Redirections(models.Model):
    objects = models.Manager()
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    name = models.TextField(blank=True, null=True)
    path = models.TextField(blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
