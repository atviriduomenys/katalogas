from importlib import import_module

import pytest
from django.apps import apps as global_apps
from django.db import IntegrityError, connection, transaction
from django.utils.timezone import now

from vitrina.users.factories import UserFactory
from vitrina.users.models import User

migration_0008 = import_module("vitrina.users.migrations.0008_user_unique_active_user_email")


def active_user(email):
    return User.objects.create(email=email, status=User.ACTIVE)


def soft_delete(user):
    """Delete the way the portal deletes: the row stays, out of `User.objects`."""
    user.deleted = True
    user.deleted_on = now()
    user.status = User.DELETED
    user.save()
    return user


@pytest.mark.django_db
def test_two_active_users_cannot_share_an_email():
    active_user("a@example.com")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            active_user("a@example.com")


@pytest.mark.django_db
def test_email_is_free_again_once_its_owner_is_deleted():
    """Deleting a user is a soft delete, and the address has to become reusable.

    A plain unique column would forbid this, which is why the constraint only
    covers the rows `UserManager` can see.
    """
    first = soft_delete(active_user("a@example.com"))
    second = active_user("a@example.com")

    assert User.objects.filter(email="a@example.com").count() == 1
    assert User.objects_with_deleted.filter(email="a@example.com").count() == 2
    assert second.pk != first.pk


@pytest.mark.django_db
def test_several_users_may_have_no_email():
    active_user(None)
    active_user(None)

    assert User.objects.filter(email__isnull=True).count() == 2


@pytest.mark.django_db
def test_several_users_may_have_a_blank_email():
    """`blank=True` means "" is a valid way to say "no address", like NULL."""
    active_user("")
    active_user("")

    assert User.objects.filter(email="").count() == 2


@pytest.mark.django_db
def test_factory_reuses_the_user_that_owns_an_email():
    """Guards the factory's own configuration, not the application.

    UserFactory keys django_get_or_create on email alone. Keyed on the other
    fields too - they are filled at random - a call passing an address that is
    already taken would miss on the lookup and go on to create a duplicate,
    which the constraint then rejects.

    Nothing else in the suite would notice: this is the only test that hands
    the factory the same address twice. Without it, going back to the old key
    leaves the suite green and surfaces later, as an IntegrityError in whatever
    test someone writes next.
    """
    first = UserFactory(email="shared@example.com")
    second = UserFactory(email="shared@example.com")

    assert second.pk == first.pk


@pytest.mark.django_db
def test_migration_names_the_duplicates_it_cannot_resolve():
    """The guard in 0008 has to explain itself, not fail on a bare index error.

    The constraint is dropped inside the test transaction so that duplicates
    can be created at all; the drop rolls back with everything else.
    """
    with connection.cursor() as cursor:
        cursor.execute("DROP INDEX unique_active_user_email")

    active_user("shared@example.com")
    active_user("shared@example.com")

    with pytest.raises(RuntimeError) as error:
        migration_0008.check_for_duplicate_active_emails(global_apps, None)

    assert "shared@example.com" in str(error.value)
