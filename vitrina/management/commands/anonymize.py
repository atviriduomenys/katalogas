from tqdm import tqdm
from django.core.management import BaseCommand

from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


class Command(BaseCommand):
    help = (
        'Anonymize database data. Warning! This is a destructive and '
        'irreversible action.'
    )

    def handle(self, *args, **kwargs):
        total = (
            User.objects.count() +
            Representative.objects.count()
        )

        ans = input(
            f"You are about to anonymize {total} rows. "
            "Are you sure? (yes/no): "
        )

        if ans != 'yes':
            print("Aborting.")
            return

        pbar = tqdm("Anonymizing", total=total)

        with pbar:
            users = {}
            for user in User.objects.all():
                fake = users[user.email] = UserFactory.build()
                user.first_name = fake.first_name
                user.last_name = fake.last_name
                user.email = fake.email
                user.phone = fake.phone
                user.set_password("secret")
                user.save()
                pbar.update(1)

            for rep in Representative.objects.all():
                fake = users.get(rep.email) or RepresentativeFactory.build()
                rep.first_name = fake.first_name
                rep.last_name = fake.last_name
                rep.phone = fake.phone
                rep.email = fake.email
                rep.save()
                pbar.update(1)
