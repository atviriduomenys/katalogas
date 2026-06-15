from django.db import migrations

TASK = "vitrina.statistics.tasks.create_dataset_stats"


def add_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="3",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
    )
    PeriodicTask.objects.get_or_create(
        task=TASK,
        defaults={"name": "Create dataset statistics", "crontab": schedule},
    )


def remove_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task=TASK).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("statistics", "0002_datasetstats_datasetstats_dataset_idx_and_more"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [migrations.RunPython(add_schedule, remove_schedule)]
