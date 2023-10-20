

from django.db import migrations, models
import django.db.models.deletion
from vitrina.settings import SITE_ID
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site



def create_redirects(apps, schema_editor):
    #SITE_ID = Site.objects.latest('id').id
    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/regulation/',
        new_path='/more/regulation/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/nuorodos/',
        new_path='/more/nuorodos/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/savokos/',
        new_path='/more/savokos/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/apie/',
        new_path='/more/apie/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/contacts/',
        new_path='/more/contacts/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/other/',
        new_path='/more/other/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/reports/',
        new_path='/more/reports/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/templates/',
        new_path='/more/templates/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/saugykla/',
        new_path='/opening-tips/saugykla/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/vadovas/',
        new_path='/opening-tips/vadovas/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/aprasas/',
        new_path='/opening-tips/aprasas/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/data-opening-tools/',
        new_path='/opening-tips/data-opening-tools/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/opening/learningmaterial/',
        new_path='/opening-tips/opening/learningmaterial/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/page/opening_faq/',
        new_path='/opening-tips/opening_faq/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/usecases/examples/',
        new_path='/projects/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/usecases/applications/',
        new_path='/projects/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/usecase/',
        new_path='/projects/add/',
    )
    redirect.save()

    redirect = Redirect.objects.create(
        site_id=SITE_ID,
        old_path='/dataset/',
        new_path='/datasets/',
    )
    redirect.save()



class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.RunPython(create_redirects)
    ]
