# Generated by Django 3.2.16 on 2022-12-05 09:10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import filer.fields.image


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.FILER_IMAGE_MODEL),
        ('vitrina_cms', '0002_alter_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='externalsite',
            name='image',
            field=filer.fields.image.FilerImageField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='image_site', to=settings.FILER_IMAGE_MODEL),
        ),
        migrations.AddField(
            model_name='learningmaterial',
            name='image',
            field=filer.fields.image.FilerImageField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='image_learning_material', to=settings.FILER_IMAGE_MODEL),
        ),
        migrations.AddField(
            model_name='newsitem',
            name='image',
            field=filer.fields.image.FilerImageField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='image_news_item', to=settings.FILER_IMAGE_MODEL),
        ),
    ]