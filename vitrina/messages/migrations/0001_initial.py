# Generated by Django 3.2.14 on 2022-09-09 11:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vitrina_datasets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('identifier', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('template', models.TextField(blank=True, null=True)),
                ('variables', models.TextField(blank=True, null=True)),
                ('subject', models.TextField(blank=True, null=True)),
                ('title', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'email_template',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='GlobalEmail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('body', models.TextField(blank=True, null=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'global_email',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='NewsletterSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('email', models.CharField(blank=True, max_length=255, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField()),
            ],
            options={
                'db_table': 'newsletter_subscription',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SentMail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('recipient', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'sent_mail',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('active', models.BooleanField()),
                ('dataset', models.ForeignKey(blank=True, db_column='dataset', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_datasets.dataset')),
                ('user', models.ForeignKey(blank=True, db_column='user', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_dataset_subscription',
                'managed': True,
            },
        ),
    ]
