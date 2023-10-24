from django.db import migrations
import datetime


def add_template_keys_to_db(apps, schema_editor):

    templates_to_insert = {
        'comment-created-sub': ['Sveiki, jūsų prenumeruojam objektui {sub_object},'
                               ' parašytas naujas komentaras.',
                               'Parašytas naujas komentaras'],
        'dataset-created-sub': ['Sveiki, jūsų prenumeruojamai organizacijai {organization},'
                               ' sukurtas naujas duomenų rinkinys {object}.',
                               'Sukurtas duomenų rinkinys'],
        'dataset-updated': ['Sveiki, duomenų rinkinys {object} buvo atnaujintas'],
        'dataset-updated-sub-type-organization': ['Sveiki, pranešame jums apie tai, kad,'
                                                 'jūsų prenumeruojamos organizacijos {organization}'
                                                 'duomenų rinkinys: {object}, buvo atnaujintas.',
                                                 'Atnaujintas duomenų rinkinys'],
        'dataset-updated-sub-type-dataset': ['Sveiki, pranešame jums apie tai, kad,'
                                            ' jūsų prenumeruojamas duomenų rinkinys'
                                            ' {organization} buvo atnaujintas.',
                                            ' Atnaujintas duomenų rinkinys'],
        'project-updated-sub': ['Sveiki, pranešame jums apie tai, kad,'
                               ' panaudos atvėjis {object} buvo atnaujintas.',
                               'Atnaujintas panaudos atvėjis'],
        'request-created-sub': ['Sveiki, jūsų prenumeruojamai organizacijai {organization},'
                               ' sukurtas naujas poreikis {object}.',
                               'Sukurtas naujas poreikis'],
        'request-updated-sub': ['Sveiki, pranešame jums apie tai, kad,'
                               ' poreikis {object} buvo atnaujintas.',
                               'Atnaujintas poreikis']
    }
    template_data = {'application-use-case-rejected': 'Sveiki, portale užregistruotas naujas pasiūlymas/pastaba:'
                                                      ' Pasiūlymo/pastabos teikėjo vardas: {title}'
                                                      ' Pasiūlymas/pastaba: {description}',
     "auth-org-representative-without-credentials": 'Buvote įtraukti į {organization} organizacijos'
                                                    ' narių sąrašo, tačiau nesate registruotas Lietuvos'
                                                    ' atvirų duomenų portale. Prašome sekite šia nuoroda,'
                                                    ' kad užsiregistruotumėte ir patvirtintumėte savo narystę'
                                                    ' organizacijoje: {url}',
     "error-in-data": 'Gautas pranešimas, kad duomenyse yra klaida: {url}'
                      'Klaida užregistruota objektui: {external_object_id},'
                      '{dataset_name}/{external_content_type}',
     "request-rejected": 'Sveiki, Jūsų poreikis duomenų rinkiniui atverti atmestas. Priežastis: {comment}',
     "request-registered": 'Sveiki, Jūsų poreikis duomenų rinkiniui atverti atmestas. Priežastis: {request_path}',
     "dataset-updated": "Sveiki, duomenų rinkinys {object} buvo atnaujintas",
     "auth-password-reset-token": 'Sveiki, norėdami susikurti naują slaptažodį turite paspausti šią nuorodą: {url}'
                                  ' Lietuvos Atvirų Duomenų Portalas',
     }
    templates_keys = {
        'error-in-data': ['url', 'external_object_id', 'dataset_name', 'external_content_type'],
        'auth-org-representative-without-credentials': ['organization', 'url'],
        'comment-created-sub': ['sub_object'],
        "dataset-created-sub": ['organization', 'object'],
        'dataset-updated': ['object'],
        'dataset-updated-sub-type-organization': ['organization', 'object'],
        'dataset-updated-sub-type-dataset': ['organization'],
        'auth-org-representative-without-credentials': ['dataset', 'url'],
        'project-updated-sub': ['object'],
        'request-rejected': ['comment'],
        'request-registered': ['request_path'],
        'request-created-sub': ['organization', 'object'],
        'request-updated-sub': ['object'],
        'auth-password-reset-token': ['url'],
        'application-use-case-rejected': ['title', 'description']
     }
    email_templates = apps.get_model('vitrina_messages', "EmailTemplate")
    for template in templates_to_insert:
        if template in templates_to_insert.keys():
            if not email_templates.objects.filter(identifier=template):
                created_template = email_templates.objects.create(
                    created=datetime.datetime.now(),
                    version=0,
                    identifier=template,
                    template=templates_to_insert[0][template],
                    subject=templates_to_insert[1][template],
                    title=templates_to_insert[1][template]
                )
                created_template.save()
            else:
                email_templates.objects.filter(identifier=template).update(template=templates_to_insert[0][template])

    for template in template_data:
        if template in template_data.keys():
            email_templates.objects.filter(identifier=template).update(template=template_data[template])

    for template in templates_keys:
        if template in templates_keys.keys():
            email_templates.objects.filter(identifier=template).update(email_keys=templates_keys[template])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_messages', '0009_auto_20231023_1557'),
    ]

    operations = [
        migrations.RunPython(add_template_keys_to_db)
    ]