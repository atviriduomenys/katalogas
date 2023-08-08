from django.db import models
from django.urls import reverse

from vitrina.users.models import User
from vitrina.orgs.models import Organization
from django.utils.translation import gettext_lazy as _


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

    def __str__(self):
        return f"Finansavimo planas {self.year}"


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


class Project(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)
    description = models.TextField(_("Aprašymas"), null=True, blank=True)
    start_date = models.DateField(_("Projekto pradžios data"), null=True, blank=True)
    end_date = models.DateField(_("Projekto pabaigos data"), null=True, blank=True)
    price = models.FloatField(_("Projekto biudžetas"), null=True, blank=True)
    procurement = models.URLField(_("Viešasis pirkimas"), null=True, blank=True)

    objects = models.Manager()

    class Meta:
        db_table = 'project'

    def __str__(self):
        return self.title


class Plan(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)
    description = models.TextField(_("Aprašymas"), null=True, blank=True)
    created = models.DateField(_("Sukurta"), auto_now_add=True, editable=False)
    deadline = models.DateField(_("Įgyvendinimo terminas"), null=True, blank=True)
    receiver = models.ForeignKey(
        'vitrina_orgs.Organization',
        verbose_name=_("Paslaugų gavėjas"),
        related_name='receiver_plans',
        on_delete=models.PROTECT
    )
    provider = models.ForeignKey(
        'vitrina_orgs.Organization',
        verbose_name=_("Paslaugų teikėjas"),
        related_name='provider_plans',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    provider_title = models.CharField(_("Paslaugų teikėjo pavadinimas"), max_length=255, null=True, blank=True)
    procurement = models.URLField(_("Nuoroda į viešąjį pirkimą"), null=True, blank=True)
    price = models.FloatField(_("Pirkimo kaina EUR"), null=True, blank=True)
    project = models.ForeignKey(Project, verbose_name=_("Projektas"), on_delete=models.PROTECT, null=True, blank=True)

    objects = models.Manager()

    class Meta:
        db_table = 'plan'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('plan-detail', args=[self.receiver.pk, self.pk])


class PlanDataset(models.Model):
    plan = models.ForeignKey(Plan, verbose_name=_("Planas"), on_delete=models.CASCADE)
    dataset = models.ForeignKey(
        'vitrina_datasets.Dataset',
        verbose_name=_('Duomenų rinkinys'),
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(_("Įtraukimo data"), auto_now_add=True, editable=False)

    class Meta:
        db_table = 'plan_dataset'
        unique_together = (('plan', 'dataset'),)

    def __str__(self):
        return str(self.plan)


class PlanRequest(models.Model):
    plan = models.ForeignKey(Plan, verbose_name=_("Planas"), on_delete=models.CASCADE)
    request = models.ForeignKey(
        'vitrina_requests.Request',
        verbose_name=_("Poreikis"),
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(_("Įtraukimo data"), auto_now_add=True, editable=False)

    class Meta:
        db_table = 'plan_request'
        unique_together = (('plan', 'request'),)

    def __str__(self):
        return str(self.plan)
