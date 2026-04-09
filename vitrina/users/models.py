from functools import cached_property
from typing import TYPE_CHECKING, Union

from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.timezone import now
from django_otp.plugins.otp_email.models import EmailDevice

from vitrina.orgs.models import Organization, Representative
from vitrina.users.managers import UserManager, DeletedUserManager

from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from vitrina.datasets.models import Dataset


class User(AbstractUser):
    ACTIVE = "active"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    LOCKED = "locked"

    STATUSES = (
        (ACTIVE, _("Aktyvus")),
        (AWAITING_CONFIRMATION, _("Laukiama patvirtinimo")),
        (SUSPENDED, _("Suspenduotas")),
        (DELETED, _("Pašalintas")),
        (LOCKED, _("Užrakintas")),
    )

    username = None
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    email = models.CharField(_("Elektroninis paštas"), max_length=255, blank=True, null=True)  # TODO should be unique.
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
    status = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=STATUSES,
        default=AWAITING_CONFIRMATION,
    )
    failed_login_attempts = models.IntegerField(default=0)
    password_last_updated = models.DateTimeField(default=now, null=True)
    is_viisp_login = models.BooleanField(
        verbose_name=_("Vartotojas prisijungęs per VIISP"),
        default=False,
        help_text=_("Indikuoja, ar vartotojas yra prisijungęs per VIISP."),
    )
    viisp_company_code = models.CharField(
        verbose_name=_("Vartotojo atstovaujama organizacija (VIISP)"),
        max_length=255,
        blank=True,
        null=True,
        editable=False,
        help_text=_("Nurodomas įmonės kodas organizacijos, kurios vardu vartotojas yra prisijungęs per VIISP."),
    )
    receive_request_email = models.BooleanField(default=False)

    # Deprecated fields bellow
    disabled = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()
    objects_with_deleted = DeletedUserManager()

    class Meta:
        db_table = "user"
        verbose_name = _("Naudotojas")
        verbose_name_plural = _("Visi naudotojai")

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

    def get_acl_parents(self):
        return [self]

    @cached_property
    def organization_content_type(self):
        return ContentType.objects.get_for_model(Organization)

    def get_representative_role_for_resource(self, resource: "Dataset") -> str | None:
        priority_roles = [
            Representative.RESOURCE_COORDINATOR,
            Representative.OPEN_DATA_COORDINATOR,
            Representative.RESOURCE_MANAGER,
            Representative.OPEN_DATA_MANAGER,
        ]
        for role in priority_roles:
            if resource.get_managers_queryset([role]).filter(user=self).exists():
                return role
        return None

    @property
    def is_manager(self) -> bool:
        return bool(self.representative_set.filter(role=Representative.RESOURCE_MANAGER))

    @property
    def is_resource_coordinator(self) -> bool:
        return bool(self.representative_set.filter(role=Representative.RESOURCE_COORDINATOR))

    @property
    def is_open_data_coordinator(self) -> bool:
        return bool(self.representative_set.filter(role=Representative.OPEN_DATA_COORDINATOR))

    @property
    def is_open_data_manager(self) -> bool:
        return bool(self.representative_set.filter(role=Representative.OPEN_DATA_MANAGER))

    @property
    def is_supervisor(self):
        return bool(self.representative_set.filter(role=Representative.SUPERVISOR))

    @property
    def is_gov_organization_resource_manager(self) -> bool:
        gov_org_content_type = self.organization_content_type
        return Representative.objects.filter(
            user=self,
            content_type=gov_org_content_type,
            object_id__in=Organization.objects.filter(kind=Organization.GOV).values_list("pk", flat=True),
            role__in=[Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER],
        ).exists()

    @property
    def can_see_manager_dataset_list_url(self):
        from vitrina.datasets.models import Dataset

        if self.is_manager or self.is_open_data_manager:
            org_ids = [rep.object_id for rep in self.representative_set.filter(role__in=Representative.MANAGER_ROLES)]
            for org_id in org_ids:
                if Dataset.objects.filter(organization=org_id):
                    return True

    @property
    def viisp_organization(self) -> Organization | None:
        if self.is_viisp_login and self.viisp_company_code:
            return Organization.objects.filter(company_code=self.viisp_company_code).first()
        return None

    @property
    def org_representatives(self) -> models.QuerySet[Representative]:
        return self.representative_set.filter(content_type=self.organization_content_type)

    @property
    def represented_org_ids(self) -> models.QuerySet[int]:
        return self.org_representatives.values_list("object_id", flat=True)

    def unlock_user(self):
        if self.status == User.LOCKED or self.status == User.ACTIVE:
            self.failed_login_attempts = 0
            self.password_last_updated = now()
            if self.deleted:
                self.status = User.DELETED
            elif not self.is_active:
                self.status = User.SUSPENDED
            elif self.emailaddress_set.first() and not self.emailaddress_set.first().verified:
                self.status = User.AWAITING_CONFIRMATION
            else:
                self.status = User.ACTIVE
            self.save()

    def lock_user(self):
        self.status = User.LOCKED
        self.save()

    def is_representative_of(self, organization: Organization, check_agreement_rights: bool = False) -> bool:
        representatives = self.org_representatives.filter(object_id=organization.id)
        if check_agreement_rights:
            representatives = representatives.filter(can_make_agreements=True)

        return representatives.exists()

    def is_resource_coordinator_for(self, organization: Organization | None) -> bool:
        if organization is None:
            return False
        org_type = self.organization_content_type
        return Representative.objects.filter(
            user=self, content_type=org_type, object_id=organization.pk, role=Representative.RESOURCE_COORDINATOR
        ).exists()

    def is_representative_for(
        self,
        obj: Union[Organization, "Dataset", None],
        roles: list[str] | None = None,
    ) -> bool:
        """
        Returns True if the user is a representative for the given object.
        The user can have this role either directly or through an organization
        they belong to. The check also includes parent objects in the ACL hierarchy.
        """
        if obj is None:
            return False

        if self.is_staff or self.is_superuser:
            return True

        parents = obj.get_acl_parents()

        # Check every node for a direct role.
        for parent in parents:
            if self._has_direct_representative_role(parent, roles):
                return True

        # Check every node for organizational membership.
        for parent in parents:
            if self._has_role_via_org_membership(parent, roles):
                return True

        return False

    def is_open_data_representative_for(
        self,
        obj: Union[Organization, "Dataset", None],
        roles: list[str] | None = None,
    ) -> bool:
        """
        Returns True if the user is an Open Data representative for the object.
        This means the user has either Open Data Coordinator or Manager role.
        """
        open_data_roles = (
            roles if roles is not None else [Representative.OPEN_DATA_COORDINATOR, Representative.OPEN_DATA_MANAGER]
        )
        return self.is_representative_for(obj, roles=open_data_roles)

    def is_coordinator_for(self, obj: Union[Organization, "Dataset", None], roles: list[str]) -> bool:
        """
        Returns True if the user is an Open Data Coordinator for the object.
        Only Direct Representative roles are checked because Organizational
        representatives cannot hold Coordinator status.
        """
        if obj is None:
            return False

        if self.is_staff or self.is_superuser:
            return True

        parents = obj.get_acl_parents()

        for parent in parents:
            if self._has_direct_representative_role(parent, roles=roles):
                return True

        return False

    def _has_direct_representative_role(
        self,
        obj: Union[Organization, "Dataset", None],
        roles: list[str] | None = None,
    ) -> bool:
        """
        Returns True if the user directly represents an object.
        """
        content_type = ContentType.objects.get_for_model(obj)
        return (
            Representative.objects.filter(
                content_type=content_type,
                object_id=obj.pk,
                role__in=roles,
                user=self,
            )
            .exclude(deleted=True)
            .exists()
        )

    def _has_role_via_org_membership(
        self,
        obj: Union[Organization, "Dataset", None],
        roles: list[str] | None = None,
    ) -> bool:
        """
        User belongs to an organization that holds a role on this object.
        Effective permission = least privileged of (user's org role, org's role on object).
        """
        content_type = ContentType.objects.get_for_model(obj)
        coordinator_to_manager = dict(zip(Representative.COORDINATOR_ROLES, Representative.MANAGER_ROLES))
        manager_equivalent_roles = [coordinator_to_manager.get(role, role) for role in roles]

        user_organization_roles = dict(
            Representative.objects.filter(user=self, content_type=self.organization_content_type)
            .exclude(deleted=True)
            .values_list("object_id", "role")
        )
        if not user_organization_roles:
            return False

        organization_representatives_on_obj = (
            Representative.objects.filter(
                content_type=content_type,
                object_id=obj.pk,
                organization_id__in=user_organization_roles.keys(),
            )
            .exclude(deleted=True)
            .values_list("organization_id", "role")
        )

        for organization_id, organization_role in organization_representatives_on_obj:
            user_role = coordinator_to_manager.get(
                user_organization_roles[organization_id], user_organization_roles[organization_id]
            )
            effective_role = max(organization_role, user_role, key=Representative.MANAGER_ROLES.index)
            if effective_role in manager_equivalent_roles:
                return True

        return False


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
        db_table = "user_table_preferences"


class OldPassword(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    password = models.CharField(max_length=128, blank=True, null=True)
    user = models.ForeignKey("User", models.CASCADE, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "old_password"


class PasswordResetToken(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    expiry_date = models.DateTimeField(blank=True, null=True)
    token = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey("User", models.CASCADE, null=True)
    used_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "password_reset_token"


class SsoToken(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    ip = models.CharField(max_length=255, blank=True, null=True)
    token = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey("User", models.CASCADE, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "sso_token"


class UserEmailDevice(EmailDevice):
    ip_address = models.CharField(
        _("IP adresas"),
        max_length=40,
        editable=False,
        db_index=True,
        null=True,
        blank=True,
    )
    user_agent = models.TextField(editable=False, null=True, blank=True)

    class Meta:
        managed = True
        db_table = "user_email_device"

    def send_mail(self, body, **kwargs):
        from vitrina.helpers import email

        email(
            [self.email or self.user.email],
            "confirm-login",
            "vitrina/email/confirm_login.md",
            {
                "full_name": str(self.user),
                "token": self.token,
            },
        )
