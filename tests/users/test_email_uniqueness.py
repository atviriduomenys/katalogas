import pytest
from django.db import IntegrityError, transaction
from django.utils.timezone import now

from vitrina.users.models import User


@pytest.mark.django_db
def test_two_active_users_cannot_share_an_email():
    User.objects.create(email="a@example.com", status=User.ACTIVE)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create(email="a@example.com", status=User.ACTIVE)


@pytest.mark.django_db
def test_email_is_free_again_once_its_owner_is_deleted():
    """Deleting a user is a soft delete, and the address has to become reusable.

    A plain unique column would forbid this, which is why the constraint only
    covers the rows `UserManager` can see.
    """
    first = User.objects.create(email="a@example.com", status=User.ACTIVE)
    first.deleted = True
    first.deleted_on = now()
    first.status = User.DELETED
    first.save()

    second = User.objects.create(email="a@example.com", status=User.ACTIVE)

    assert User.objects.filter(email="a@example.com").count() == 1
    assert User.objects_with_deleted.filter(email="a@example.com").count() == 2
    assert second.pk != first.pk


@pytest.mark.django_db
def test_several_users_may_have_no_email():
    User.objects.create(email=None, status=User.ACTIVE)
    User.objects.create(email=None, status=User.ACTIVE)

    assert User.objects.filter(email__isnull=True).count() == 2


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
    from vitrina.users.factories import UserFactory

    first = UserFactory(email="shared@example.com")
    second = UserFactory(email="shared@example.com")

    assert second.pk == first.pk


@pytest.mark.django_db
def test_several_users_may_have_a_blank_email():
    """`blank=True` means "" is a valid way to say "no address", like NULL."""
    User.objects.create(email="", status=User.ACTIVE)
    User.objects.create(email="", status=User.ACTIVE)

    assert User.objects.filter(email="").count() == 2


@pytest.mark.django_db
def test_migration_names_the_duplicates_it_cannot_resolve():
    """The guard in 0008 has to explain itself, not fail on a bare index error.

    The constraint is dropped inside the test transaction so that duplicates
    can be created at all; the drop rolls back with everything else.
    """
    from importlib import import_module

    from django.apps import apps as global_apps
    from django.db import connection

    migration = import_module("vitrina.users.migrations.0008_user_unique_active_user_email")

    with connection.cursor() as cursor:
        cursor.execute("DROP INDEX unique_active_user_email")

    User.objects.create(email="shared@example.com", status=User.ACTIVE)
    User.objects.create(email="shared@example.com", status=User.ACTIVE)

    with pytest.raises(RuntimeError) as error:
        migration.check_for_duplicate_active_emails(global_apps, None)

    assert "shared@example.com" in str(error.value)
