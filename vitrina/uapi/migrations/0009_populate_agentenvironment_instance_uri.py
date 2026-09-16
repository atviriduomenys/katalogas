from django.db import migrations
from django.db.migrations.exceptions import IrreversibleError

from vitrina.uapi.utils.utils import generate_agent_instance_uri


def assign_instance_uris(apps, schema_editor):
    AgentEnvironment = apps.get_model("vitrina_uapi", "AgentEnvironment")

    # Archived environments too: 0010 makes the field unique and NOT NULL.
    for agent_environment in AgentEnvironment.objects.filter(instance_uri__isnull=True).only("pk"):
        agent_environment.instance_uri = generate_agent_instance_uri()
        agent_environment.save(update_fields=["instance_uri"])


def refuse_rollback(apps, schema_editor):
    # Rolling back past 0008 drops the column, and applying 0009 again would issue new identifiers.
    # A deployed agent keeps the `agent_id` it was given, so its tokens would stop matching.
    raise IrreversibleError(
        "vitrina_uapi.0009 cannot be reversed: AgentEnvironment.instance_uri is the `aud` of deployed agents, "
        "and a rollback would replace every identifier with a new one."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_uapi", "0008_agentenvironment_instance_uri"),
    ]

    operations = [
        migrations.RunPython(assign_instance_uris, refuse_rollback),
    ]
