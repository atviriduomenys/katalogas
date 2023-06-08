import os
from typer import run, Option
import django
from django.apps import apps


def main():
    DatasetEvent = apps.get_model('vitrina_datasets', 'DatasetEvent')
    Dataset = apps.get_model('vitrina_datasets', 'Dataset')
    Revision = apps.get_model('reversion', 'Revision')
    Version = apps.get_model('reversion', 'Version')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for event in DatasetEvent.objects.exclude(dataset_id__isnull=True):
        content_type = ContentType.objects.get_for_model(Dataset)
        dataset = Dataset.objects.get(pk=event.dataset_id)
        revision = Revision.objects.create(
            date_created=event.created,
            user=event.user_0,
            comment=event.type or "",
        )
        Version.objects.create(
            object_id=event.dataset_id,
            content_type=content_type,
            object_repr=str(dataset),
            format="json",
            db="default",
            revision=revision
        )




if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
    django.setup()
    run(main)