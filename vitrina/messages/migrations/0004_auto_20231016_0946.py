# Generated by Django 3.2.22 on 2023-10-16 06:46

from django.db import migrations
import datetime


def change_existing_keys_in_template(apps, schema_editor):
    templates_to_insert = {
                            'error-in-data': 'Pranešimas apie klaida duomenyse',
                            'auth-org-representative-without-credentials': 'Kvietimas prisijungti prie atvirų duomenų portalo'
                           }
    template_data = {"application-use-case-rejected": """Sveiki,
            portale užregistruotas naujas pasiūlymas/pastaba: <br>
            Pasiūlymo/pastabos teikėjo vardas: {0} <br>
            Pasiūlymas/pastaba: {1}    
     """,
     "auth-org-representative-without-credentials": """ Buvote įtraukti į {0} organizacijos
         narių sąrašo, tačiau nesate registruotas Lietuvos
         atvirų duomenų portale. Prašome sekite šia nuoroda,
         kad užsiregistruotumėte ir patvirtintumėte savo narystę
         organizacijoje: {1}       
     """,
     "error-in-data": """Gautas pranešimas, kad duomenyse yra klaida:
            {0}
            Klaida užregistruota objektui: {1},
            {2}/{3}""",
     "request-rejected": """Sveiki, Jūsų poreikis duomenų rinkiniui atverti atmestas. <br><br>Priežastis:<br><br> {0}""",
     "dataset-updated": "Sveiki, duomenų rinkinys {0} buvo atnaujintas",
     "auth-password-reset-token": """
        Sveiki, norėdami susikurti naują slaptažodį turite paspausti šią nuorodą: <br><br> {0}<br><br>
        Lietuvos Atvirų Duomenų Portalas    
     """,
     }
    email_templates = apps.get_model('vitrina_messages', "EmailTemplate")
    for template in template_data:
        if template in templates_to_insert.keys():
            created_template = email_templates.objects.create(
                created=datetime.datetime.now(),
                version=0,
                identifier=template,
                template=template_data[template],
                subject=templates_to_insert[template],
                title=templates_to_insert[template]
            )
            created_template.save()
        else:
            email_templates.objects.filter(identifier=template).update(template=template_data[template])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_messages', '0003_auto_20220928_0827'),
    ]

    operations = [
        migrations.RunPython(change_existing_keys_in_template)
    ]
