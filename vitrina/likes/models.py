from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from vitrina.datasets.models import Dataset
from vitrina.datasets.models import HarvestingResult
from vitrina.users.models import User


# TODO: Make generic.
class UserLike(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    request_id = models.BigIntegerField(blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'user_like'


# TODO: Merge into UserLike.
class UserVote(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    rating = models.IntegerField()
    dataset = models.ForeignKey(Dataset, models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    harvested = models.ForeignKey(HarvestingResult, models.CASCADE, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'user_vote'


class Like(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'like'
        unique_together = ['user', 'content_type', 'object_id']

    def __str__(self):
        return str(self.user)
