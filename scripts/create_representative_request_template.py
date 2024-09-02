import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from typer import run
from django.core.files import File
from vitrina.orgs.models import Template


def main():
    """
    Create representative request template
    """

    if not Template.objects.filter(identifier=Template.REPRESENTATIVE_REQUEST_ID):
        template = Template(
            identifier=Template.REPRESENTATIVE_REQUEST_ID,
            text="atsisiųsti prašymo dokumento šabloną",
        )

        with open('scripts/representative-request-template.doc', 'rb') as f:
            template.document = File(f, name='Rašto dėl koordinatoriaus paskyrimo pavyzdys.doc')
            template.save()


if __name__ == '__main__':
    run(main)
