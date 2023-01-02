import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from datetime import datetime
from django.utils import timezone
from slugify import slugify
from tqdm import tqdm
from typer import run

from django.contrib.contenttypes.models import ContentType
from djangocms_blog.cms_appconfig import BlogConfig
from djangocms_blog.models import Post
from vitrina.cms.models import NewsItem, FileResource


def main():
    """
    Migrate NewsItem objects to djangocms_blog Post.
    """

    pbar = tqdm("Migrating news items", total=NewsItem.objects.count())

    config = BlogConfig.objects.first()
    config.app_data['config'].template_prefix = "vitrina/cms"
    config.save()

    with pbar:
        for item in NewsItem.objects.all():
            if item.author_name:
                item.body = f'<p>Autorius: {item.author_name}</p>{item.body}'
                item.summary = f'<p>Autorius: {item.author_name}</p>{item.summary}'

            if item.published:
                date_published = timezone.make_aware(datetime(
                    item.published.year,
                    item.published.month,
                    item.published.day
                ), timezone.get_current_timezone())
            else:
                date_published = None
            post = Post.objects.create(
                date_created=item.created,
                date_modified=item.modified,
                date_published=date_published,
                publish=item.is_public,
                slug=slugify(item.title),
                title=item.title,
                abstract=item.summary,
                post_text=item.body,
                app_config=config,
                main_image=item.image
            )
            for file in FileResource.objects.filter(
                content_type=ContentType.objects.get_for_model(NewsItem),
                object_id=item.pk
            ):
                file.content_type = ContentType.objects.get_for_model(Post)
                file.object_id = post.pk
                file.save()
            pbar.update(1)


if __name__ == '__main__':
    run(main)
