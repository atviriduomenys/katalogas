from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_uapi", "0010_alter_agentenvironment_instance_uri"),
    ]

    operations = [
        migrations.RenameField(
            model_name="agentenvironment",
            old_name="instance_uri",
            new_name="uri",
        ),
    ]
