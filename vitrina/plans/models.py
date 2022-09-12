from django.db import models

from vitrina.users.models import User
from vitrina.orgs.models import Organization


class FinancingPlan(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    financed_datasets = models.IntegerField(blank=True, null=True)
    financing_plan_state_id = models.BigIntegerField(blank=True, null=True)
    projected_cost = models.IntegerField(blank=True, null=True)
    projected_datasets = models.IntegerField(blank=True, null=True)
    received_financing = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', blank=True, null=True)
    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'financing_plan'
        unique_together = (('organization', 'year'),)


class FinancingPlanState(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    details = models.TextField(blank=True, null=True)
    financing_plan_id = models.BigIntegerField(blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'financing_plan_state'


class NationalFinancingPlan(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    confirmation_date = models.DateTimeField(blank=True, null=True)
    confirmed = models.BooleanField(blank=True, null=True)
    confirmed_budget = models.BigIntegerField(blank=True, null=True)
    confirmed_by = models.BigIntegerField(blank=True, null=True)
    estimated_budget = models.BigIntegerField(blank=True, null=True)
    year = models.IntegerField(unique=True, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'national_financing_plan'
