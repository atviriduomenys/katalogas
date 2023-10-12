from django.contrib.auth.models import AbstractUser
from django.db import models

from vitrina.orgs.models import Organization, Representative
from vitrina.users.managers import UserManager


class User(AbstractUser):
    username = None
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    email = models.CharField(unique=True, max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    organization = models.ForeignKey(Organization, models.SET_NULL, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    needs_password_change = models.BooleanField(default=False)
    year_of_birth = models.IntegerField(blank=True, null=True)
    disabled = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = 'user'

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

    def get_acl_parents(self):
        return [self]

    @property
    def is_manager(self):
        return bool(self.representative_set.filter(role=Representative.MANAGER))

    @property
    def is_supervisor(self):
        return bool(self.representative_set.filter(role=Representative.SUPERVISOR))
                
    @property
    def can_see_manager_dataset_list_url(self):
        from vitrina.datasets.models import Dataset
        if self.is_manager:
            org_ids = [rep.object_id for rep in self.representative_set.filter(role=Representative.MANAGER)]
            for org_id in org_ids:
                if Dataset.objects.filter(organization=org_id):
                    return True

class UserTablePreferences(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    table_column_string = models.TextField(blank=True, null=True)
    table_id = models.CharField(max_length=255, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'user_table_preferences'


class OldPassword(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    password = models.CharField(max_length=60, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'old_password'


class PasswordResetToken(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    expiry_date = models.DateTimeField(blank=True, null=True)
    token = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING)
    used_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'password_reset_token'


class SsoToken(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    ip = models.CharField(max_length=255, blank=True, null=True)
    token = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'sso_token'
