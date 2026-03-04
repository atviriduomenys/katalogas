from django.db import migrations


def move_agents_to_service(apps, schema_editor):
    Agent = apps.get_model("vitrina_uapi", "Agent")
    Dataset = apps.get_model("vitrina_datasets", "Dataset")

    for agent in Agent.objects.exclude(service__isnull=True):
        Dataset.objects.filter(pk=agent.service.pk).update(agent=agent)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('vitrina_uapi', '0006_remove_agent_agent_address_and_more'),
        ('vitrina_datasets', '0039_dataset_agent'),
    ]

    operations = [
        migrations.RunPython(move_agents_to_service, migrations.RunPython.noop),
        migrations.RemoveField(model_name='agent', name='service'),
    ]
