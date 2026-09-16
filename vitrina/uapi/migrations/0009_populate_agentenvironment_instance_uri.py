from django.db import migrations

from vitrina.uapi.utils.utils import generate_agent_instance_uri


def assign_instance_uris(apps, schema_editor):
    AgentEnvironment = apps.get_model("vitrina_uapi", "AgentEnvironment")

    # Archived environments too: 0010 makes the field unique and NOT NULL.
    for agent_environment in AgentEnvironment.objects.filter(instance_uri__isnull=True).only("pk"):
        agent_environment.instance_uri = generate_agent_instance_uri()
        agent_environment.save(update_fields=["instance_uri"])


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_uapi", "0008_agentenvironment_instance_uri"),
    ]

    operations = [
        migrations.RunPython(assign_instance_uris, migrations.RunPython.noop),
    ]
