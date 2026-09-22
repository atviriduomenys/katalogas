from django.db import migrations, models

import vitrina.uapi.utils.utils
from vitrina.uapi.utils.utils import generate_agent_instance_uri


def lock_and_assign_missing_instance_uris(apps, schema_editor):
    AgentEnvironment = apps.get_model("vitrina_uapi", "AgentEnvironment")

    # The app still running the previous release can insert an environment without `instance_uri` after 0009.
    # Block writes until this migration commits, so none can slip in before the NOT NULL below.
    table = schema_editor.quote_name(AgentEnvironment._meta.db_table)
    schema_editor.execute(f"LOCK TABLE {table} IN SHARE ROW EXCLUSIVE MODE")

    for agent_environment in AgentEnvironment.objects.filter(instance_uri__isnull=True).only("pk"):
        agent_environment.instance_uri = generate_agent_instance_uri()
        agent_environment.save(update_fields=["instance_uri"])


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_uapi", "0009_populate_agentenvironment_instance_uri"),
    ]

    operations = [
        migrations.RunPython(lock_and_assign_missing_instance_uris, migrations.RunPython.noop),
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
