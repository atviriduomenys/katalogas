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
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    harvested = models.ForeignKey(HarvestingResult, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'user_vote'
