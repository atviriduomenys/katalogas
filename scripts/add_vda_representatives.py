import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from typer import run
import pandas as pd
from tqdm import tqdm
from django.contrib.sites.models import Site
from django.db.models import Q
from django.urls import reverse
from itsdangerous import URLSafeSerializer
from django.contrib.contenttypes.models import ContentType
from vitrina import settings
from vitrina.helpers import email
from vitrina.orgs.views import ORGANIZATION_REPRESENTATIVE_CREATE_EMAIL_IDENTIFIER
from vitrina.orgs.models import Organization, Representative
from vitrina.users.models import User


def main():
    """
    Create VDA representatives
    """

    data = pd.read_excel('scripts/institucijos.xlsx')
    pbar = tqdm("Creating VDA representatives", total=len(data))

    rep_info = [
        ('igne.cesnakauskiene@stat.gov.lt', '+37064048307'),
        ('benas.denisovas@stat.gov.lt', '+37065683876'),
        ('laurynas.grusas@stat.gov.lt', '+37063367105')
    ]

    sent_email = []
    for i, row in data.iterrows():
        company_code = row["JAR kodas"]
        title = row["Institucija"]

        organization = Organization.objects.filter(
            Q(company_code=company_code) |
            Q(title=title)
        ).first()

        if not organization:
            organization = Organization.add_root(
                title=title,
                company_code=company_code,
                is_public=True
            )

        for email_address, phone in rep_info:
            if not Representative.objects.filter(
                content_type=ContentType.objects.get_for_model(Organization),
                object_id=organization.pk,
                email__icontains=email_address
            ):
                user = User.objects.filter(email__icontains=email_address).first()

                representative = Representative.objects.create(
                    content_type=ContentType.objects.get_for_model(Organization),
                    object_id=organization.pk,
                    email=user.email if user else email_address,
                    user=user,
                    role=Representative.MANAGER,
                    phone=phone
                )

                if not user and email_address not in sent_email:
                    sent_email.append(email_address)

                    serializer = URLSafeSerializer(settings.SECRET_KEY)
                    token = serializer.dumps({
                        "representative_id": representative.pk,
                        "subscribe": True
                    })
                    url = "https://%s%s" % (
                        Site.objects.get_current().domain,
                        reverse('representative-register', kwargs={'token': token})
                    )

                    email(
                        [email_address], ORGANIZATION_REPRESENTATIVE_CREATE_EMAIL_IDENTIFIER,
                        'vitrina/emails/request_for_organization_member_add.md', {
                            'organization': organization.title,
                            'link': url
                        })
        pbar.update(1)


if __name__ == '__main__':
    run(main)
