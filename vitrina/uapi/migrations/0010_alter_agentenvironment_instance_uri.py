import uuid

from django.db import migrations, models

# `default` below must stay a reference: Django compares it with the model's field.
import vitrina.uapi.utils.utils


# A copy of `vitrina.uapi.utils.utils.generate_agent_uri`, so later changes there do not alter this migration.
def generate_agent_uri() -> str:
    return f"https://data.gov.lt/id/dcat/Agent/{uuid.uuid4()}"


def lock_and_assign_missing_instance_uris(apps, schema_editor):
    AgentEnvironment = apps.get_model("vitrina_uapi", "AgentEnvironment")

    # The app still running the previous release can insert an environment without `instance_uri` after 0009.
    # Block writes until this migration commits, so none can slip in before the NOT NULL below.
    table = schema_editor.quote_name(AgentEnvironment._meta.db_table)
    schema_editor.execute(f"LOCK TABLE {table} IN SHARE ROW EXCLUSIVE MODE")

    for agent_environment in AgentEnvironment.objects.filter(instance_uri__isnull=True).only("pk"):
        agent_environment.instance_uri = generate_agent_uri()
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
                default=vitrina.uapi.utils.utils.generate_agent_uri,
                editable=False,
                help_text="Agento aplinkos identifikatorius, sugeneruojamas sukuriant aplinką. Naudojamas kaip prieigos rakto `aud` reikšmė.",
                max_length=255,
                unique=True,
                verbose_name="Agento identifikatorius",
            ),
        ),
    ]
