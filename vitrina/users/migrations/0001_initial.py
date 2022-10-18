# Generated by Django 3.2.14 on 2022-08-16 06:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vitrina_orgs', '0001_initial')
    ]

    operations = [
        migrations.CreateModel(
            name='OldPassword',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('password', models.CharField(blank=True, max_length=60, null=True)),
            ],
            options={
                'db_table': 'old_password',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('expiry_date', models.DateTimeField(blank=True, null=True)),
                ('token', models.CharField(blank=True, max_length=255, null=True)),
                ('used_date', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'password_reset_token',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='SsoToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('ip', models.CharField(blank=True, max_length=255, null=True)),
                ('token', models.CharField(blank=True, max_length=36, null=True, unique=True)),
            ],
            options={
                'db_table': 'sso_token',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('email', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=255, null=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('last_name', models.CharField(blank=True, max_length=255, null=True)),
                ('password', models.CharField(blank=True, max_length=60, null=True)),
                ('role', models.CharField(blank=True, max_length=255, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('phone', models.CharField(blank=True, max_length=255, null=True)),
                ('needs_password_change', models.BooleanField()),
                ('year_of_birth', models.IntegerField(blank=True, null=True)),
                ('disabled', models.BooleanField()),
                ('suspended', models.BooleanField()),
                ('organization',  models.ForeignKey(to='vitrina_orgs.organization', on_delete=models.SET_NULL, blank=True, null=True))
            ],
            options={
                'db_table': 'user',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='UserTablePreferences',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('table_column_string', models.TextField(blank=True, null=True)),
                ('table_id', models.CharField(blank=True, max_length=255, null=True)),
                ('user_id', models.BigIntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'user_table_preferences',
                'managed': False,
            },
        ),
    ]
