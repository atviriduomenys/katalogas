# Generated by Django 3.2.16 on 2022-11-14 06:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CmsMenuItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
            ],
            options={
                'db_table': 'cms_menu_item',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CssRuleOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('active', models.BooleanField(blank=True, null=True)),
                ('css_order', models.IntegerField(blank=True, null=True)),
                ('css_override', models.TextField(blank=True, null=True)),
                ('expires', models.DateTimeField(blank=True, null=True)),
                ('title', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'css_rule_override',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ExternalSite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('imageuuid', models.CharField(blank=True, max_length=36, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('type', models.CharField(blank=True, choices=[('EU_COMISSION_PORTAL', 'Europos komisijos portalai'), ('EU_LAND', 'EU šalys'), ('OTHER_LAND', 'Kitos šalys')], max_length=255, null=True),),
                ('url', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'external_site',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Faq',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('answer', models.TextField(blank=True, null=True)),
                ('question', models.TextField(blank=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'faq',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='FileResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('filename', models.CharField(blank=True, max_length=255, null=True)),
                ('identifier', models.CharField(blank=True, max_length=36, null=True)),
                ('mime_type', models.CharField(blank=True, max_length=255, null=True)),
                ('obj_class', models.CharField(blank=True, max_length=255, null=True)),
                ('obj_id', models.BigIntegerField(blank=True, null=True)),
                ('size', models.BigIntegerField(blank=True, null=True)),
                ('type', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'file_resource',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='TermsOfUse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('description', models.TextField(blank=True, null=True)),
                ('file', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('body', models.TextField(blank=True, null=True)),
                ('imageuuid', models.CharField(blank=True, max_length=36, null=True)),
                ('published', models.DateField(blank=True, null=True)),
            ],
            options={
                'db_table': 'terms_of_use',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='NewsItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('author', models.TextField(blank=True, null=True)),
                ('body', models.TextField(blank=True, null=True)),
                ('slug', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('tags', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('uuid', models.CharField(blank=True, max_length=36, null=True, unique=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('imageuuid', models.CharField(blank=True, max_length=36, null=True)),
                ('summary', models.TextField(blank=True, null=True)),
                ('author_name', models.TextField(blank=True, null=True)),
                ('is_public', models.BooleanField(blank=True, null=True)),
                ('published', models.DateField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'news_item',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='LearningMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('comment', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('learning_material_id', models.BigIntegerField(blank=True, null=True)),
                ('status', models.CharField(blank=True, max_length=255, null=True)),
                ('topic', models.CharField(blank=True, max_length=255, null=True)),
                ('video_url', models.CharField(blank=True, max_length=255, null=True)),
                ('imageuuid', models.CharField(blank=True, max_length=36, null=True)),
                ('summary', models.TextField(blank=True, null=True)),
                ('author_name', models.TextField(blank=True, null=True)),
                ('published', models.DateField(blank=True, null=True)),
                ('uuid', models.CharField(blank=True, max_length=36, null=True, unique=True)),
                ('requested', models.IntegerField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'learning_material',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CmsPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('body', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('page_order', models.IntegerField(blank=True, null=True)),
                ('published', models.BooleanField()),
                ('slug', models.TextField(blank=True, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('type', models.IntegerField(blank=True, null=True)),
                ('language', models.CharField(blank=True, max_length=255, null=True)),
                ('list_children', models.BooleanField()),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_cms.cmspage')),
            ],
            options={
                'db_table': 'adp_cms_page',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CmsAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('file_data', models.TextField(blank=True, null=True)),
                ('filename', models.CharField(blank=True, max_length=255, null=True)),
                ('mime_type', models.CharField(blank=True, max_length=255, null=True)),
                ('cms_page', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_cms.cmspage')),
            ],
            options={
                'db_table': 'cms_attachment',
                'managed': False,
            },
        ),
    ]