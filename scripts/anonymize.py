import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import dataset as dataset
from tqdm import tqdm
from faker import Faker
from django.contrib.auth.hashers import make_password


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
        fake = Faker()
        Faker.seed(0)

        for user in db['user'].all():
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f'{first_name}.{last_name}{fake.random_number(digits=3)}@example.com'
            phone = fake.phone_number()
            data = {
                'id': user['id'],
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'password': make_password("secret").split("$", 1)[1]
            }
            users[user['email']] = data
            db['user'].update(data, ['id'])
            pbar.update(1)

        for rep in db['representative'].all():
            related_user = users.get(rep['email'])
            if related_user:
                first_name = related_user['first_name']
                last_name = related_user['last_name']
                email = related_user['email']
                phone = related_user['phone']
            else:
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = f'{first_name}.{last_name}{fake.random_number(digits=3)}@example.com'
                phone = fake.phone_number()
            data = {
                'id': rep['id'],
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
            }
            db['representative'].update(data, ['id'])
            pbar.update(1)
