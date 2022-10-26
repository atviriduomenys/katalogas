# Generated by Django 3.2.15 on 2022-09-19 07:47

from django.db import migrations, models


def fix_icons(apps, schema_editor):
    Category = apps.get_model("vitrina_classifiers", "Category")
    categories = Category.objects.all()
    for cat in categories:
        if cat.icon is None:
            cat.icon = ""
        if cat.icon:
            cat.featured = True
        if cat.icon == 'vaccine':
            cat.icon = 'fa-hand-holding-heart'
        if cat.icon == 'trumpet':
            cat.icon = 'fa-theater-masks'
        if cat.icon == 'retirement-plan':
            cat.icon = 'fa-universal-access'
        if cat.icon == 'pantheon':
            cat.icon = 'fa-columns'
        if cat.icon == 'oil':
            cat.icon = 'fa-oil-can'
        if cat.icon == 'nature':
            cat.icon = 'fa-tree'
        if cat.icon == 'marketing':
            cat.icon = 'fa-handshake'
        if cat.icon == 'electricity-tower':
            cat.icon = 'fa-broadcast-tower'
        if cat.icon == 'cityscape':
            cat.icon = 'fa-city'
        if cat.icon == 'books':
            cat.icon = 'fa-book'
        if cat.icon == 'balance':
            cat.icon = 'fa-balance-scale'
        if cat.icon == 'analysis':
            cat.icon = 'fa-microscope'
        if cat.icon == 'airplane':
            cat.icon = 'fa-plane'
        if cat.icon == 'accounting':
            cat.icon = 'fa-tractor'
        cat.save(update_fields=['icon', 'featured'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_classifiers', '0004_rename_parent_id_category_parent'),
    ]

    operations = [
        migrations.RunPython(fix_icons),
    ]
