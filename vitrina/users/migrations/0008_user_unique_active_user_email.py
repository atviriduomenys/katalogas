from django.db import migrations, models
from django.db.models import Count


def check_for_duplicate_active_emails(apps, schema_editor):
    """Stop with something readable if the constraint cannot be applied.

    `UserManager._create_user` and the registration forms check for duplicates
    and then save, so two concurrent requests can still get through, and the
    database has never forbidden it. If such a pair exists, AddConstraint fails
    with a bare "duplicate key value violates unique constraint" in the middle
    of a deployment. Naming the addresses makes that fixable.

    Nothing is resolved here on purpose: merging two accounts, or deciding
    which one keeps the address, is not a choice a migration should make.
    """
    User = apps.get_model("vitrina_users", "User")
    duplicates = (
        User.objects.filter(deleted__isnull=True, deleted_on__isnull=True)
        .exclude(status="deleted")
        .exclude(email__isnull=True)
        .exclude(email="")
        .values("email")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .values_list("email", flat=True)
    )
    found = list(duplicates[:20])
    if found:
        raise RuntimeError(
            "Cannot make email unique among active users: these addresses are held by more "
            "than one of them:\n  " + "\n  ".join(found) + "\n"
            "Resolve them first - merge the accounts, or delete the one that should not keep "
            "the address - and run the migration again."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_users', '0007_rename_version_user_model_version'),
    ]

    operations = [
        migrations.RunPython(check_for_duplicate_active_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted__isnull', True), ('deleted_on__isnull', True), models.Q(('status', 'deleted'), _negated=True), models.Q(('email', ''), _negated=True)), fields=('email',), name='unique_active_user_email'),
        ),
    ]
