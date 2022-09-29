from django.core.management import BaseCommand

from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


class Command(BaseCommand):
    help = 'Depersonalizes user data'

    def handle(self, *args, **kwargs):
        already_depersonalized = []
        for user in User.objects.all():
            depersonalized_user = UserFactory.build()
            user.first_name = depersonalized_user.first_name
            user.last_name = depersonalized_user.last_name
            user.phone = depersonalized_user.phone
            user.set_password("secret")
            for rep in Representative.objects.filter(email=user.email):
                rep.first_name = depersonalized_user.first_name
                rep.last_name = depersonalized_user.last_name
                rep.phone = depersonalized_user.phone
                rep.email = depersonalized_user.email
                rep.save()
                already_depersonalized.append(rep.pk)
            user.email = depersonalized_user.email
            user.save()

        for rep in Representative.objects.exclude(pk__in=already_depersonalized):
            depersonalized_user = RepresentativeFactory.build()
            rep.first_name = depersonalized_user.first_name
            rep.last_name = depersonalized_user.last_name
            rep.phone = depersonalized_user.phone
            rep.email = depersonalized_user.email
            rep.save()
