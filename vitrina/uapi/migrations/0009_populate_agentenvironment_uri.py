import uuid

from django.db import migrations
from django.db.migrations.exceptions import IrreversibleError


# A copy of `vitrina.uapi.utils.utils.generate_agent_uri`, so later changes there do not alter this migration.
def generate_agent_uri() -> str:
    return f"https://data.gov.lt/id/dcat/Agent/{uuid.uuid4()}"


def assign_uris(apps, schema_editor):
    AgentEnvironment = apps.get_model("vitrina_uapi", "AgentEnvironment")

    # Archived environments too: 0010 makes the field unique and NOT NULL.
    for agent_environment in AgentEnvironment.objects.filter(uri__isnull=True).only("pk"):
        agent_environment.uri = generate_agent_uri()
        agent_environment.save(update_fields=["uri"])


def refuse_rollback(apps, schema_editor):
    # Rolling back past 0008 drops the column, and applying 0009 again would issue new identifiers.
    # A deployed agent keeps the `resource_server_id` it was given, so its tokens would stop matching.
    raise IrreversibleError(
        "vitrina_uapi.0009 cannot be reversed: AgentEnvironment.uri is the `aud` of deployed agents, "
        "and a rollback would replace every identifier with a new one."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_uapi", "0008_agentenvironment_uri"),
    ]

    operations = [
        migrations.RunPython(assign_uris, refuse_rollback),
    ]
