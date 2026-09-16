from django.db import migrations, models

import vitrina.uapi.utils.utils


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_uapi", "0009_populate_agentenvironment_instance_uri"),
    ]

    operations = [
        migrations.AlterField(
            model_name="agentenvironment",
            name="instance_uri",
            field=models.CharField(
                default=vitrina.uapi.utils.utils.generate_agent_instance_uri,
                editable=False,
                help_text="Spintos instancijos identifikatorius, sugeneruojamas sukuriant aplinką. Agentas jį naudoja kaip prieigos rakto `aud` reikšmę.",
                max_length=255,
                unique=True,
                verbose_name="Agento identifikatorius",
            ),
        ),
    ]
