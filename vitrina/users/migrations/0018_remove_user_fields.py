from django.db import migrations
from django.db.utils import ProgrammingError, OperationalError


def remove_field_if_exists(apps, schema_editor, model_name, field_name):
    cursor = schema_editor.connection.cursor()
    try:
        cursor.execute(f"ALTER TABLE {model_name} DROP COLUMN IF EXISTS {field_name};")
    except (ProgrammingError, OperationalError) as e:
        print(f"Error removing field {field_name} from {model_name}: {str(e)}")
    finally:
        cursor.close()


def remove_user_fields(apps, schema_editor):
    remove_field_if_exists(apps, schema_editor, "old_password", "user_id")

    remove_field_if_exists(apps, schema_editor, "password_reset_token", "user_id")

    remove_field_if_exists(apps, schema_editor, "sso_token", "user_id")


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_users", "0017_auto_20241114_0847"),
    ]

    operations = [
        migrations.RunPython(remove_user_fields),
    ]
