from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_uapi", "0007_move_agent_to_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="agentenvironment",
            name="instance_uri",
            field=models.CharField(editable=False, max_length=255, null=True),
        ),
    ]
