import os
import django
from django.contrib.auth.hashers import make_password

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import dataset as dataset
from tqdm import tqdm

from vitrina.orgs.factories import RepresentativeFactory
from vitrina.users.factories import UserFactory


db = dataset.connect('postgresql://adp:secret@127.0.0.1:5432/adp-dev')

total = (
    db['user'].count() +
    db['representative'].count()
)

ans = input(
    f"You are about to anonymize {total} rows. "
    "Are you sure? (yes/no): "
)

if ans != 'yes':
    print("Aborting.")
else:
    pbar = tqdm("Anonymizing", total=total)

    with pbar:
        users = {}
        for user in db['user'].all():
            fake = users[user['email']] = UserFactory.build()
            data = {
                'id': user['id'],
                'first_name': fake.first_name,
                'last_name': fake.last_name,
                'email': fake.email,
                'phone': fake.phone,
                'password': make_password("secret").split("$", 1)[1]
            }
            db['user'].update(data, ['id'])
            pbar.update(1)

        for rep in db['representative'].all():
            fake = users.get(rep['email']) or RepresentativeFactory.build()
            data = {
                'id': rep['id'],
                'first_name': fake.first_name,
                'last_name': fake.last_name,
                'email': fake.email,
                'phone': fake.phone,
            }
            db['representative'].update(data, ['id'])
            pbar.update(1)
