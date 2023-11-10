import os
import django
from slugify import slugify
from collections import Counter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from vitrina.datasets.models import Dataset
from typer import run


def main():
    all_tags = Dataset.tags.tag_model.objects.all()

    for tag in all_tags:
        stripped = tag.name.strip()
        name = tag.name
        slug = tag.slug

        if not name.isspace():
            if len(stripped) > 0:
                if len(stripped) == len(slug):
                    exists = Dataset.tags.tag_model.objects.filter(name=stripped.title()).exists()
                    tag.name = stripped.title()
                    if exists:
                        existing = Dataset.tags.tag_model.objects.filter(name=stripped.title()).get()
                        if len(existing.name.strip()) != len(existing.slug):
                            items = Dataset.objects.filter(tags__name__in=existing.name)
                            for dataset in items:
                                dataset.tags.remove(existing)
                                dataset.tags.add(tag)
                            Dataset.tags.tag_model.objects.filter(pk=existing.pk).delete()
                    tag.save()
                if len(stripped) != len(slug):
                    slug_sub = slug.split('_')[0]
                    original_tag = Dataset.tags.tag_model.objects.filter(slug=slug_sub).exists()
                    if original_tag:
                        ot = Dataset.tags.tag_model.objects.filter(slug=slug_sub).get()
                        items = Dataset.objects.filter(tags__name__in=name)
                        for dataset in items:
                            dataset.tags.remove(tag)
                            dataset.tags.add(ot)
                        Dataset.tags.tag_model.objects.filter(pk=tag.pk).delete()


if __name__ == '__main__':
    run(main)
