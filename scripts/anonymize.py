import sys
import uuid
from typing import Set

import bcrypt
import dataset
from tqdm import tqdm

from faker import Faker
from typer import Argument
from typer import Option
from typer import confirm
from typer import run


def main(
    uri: str = Argument(..., help=(
        "Database URI (postgresql://user:pass@host:port/db)"
    )),
    yes: bool = Option(False, help="Do not ask anything, just do it"),
):
    """
    Anonymize database.

    WARGNING! This command will modify database data, without possibility to
    restore it. So before using this command, make sure to pass corect database
    connection string.
    """
    db = dataset.connect(uri)

    tables = [
        'user',
        'representative',
        'old_password',
        'password_reset_token',
        'newsletter_subscription',
        'partner_application',
        'sso_token',
        'suggestion',
        'comment',
        'request_event',
    ]

    total = sum([db[t].count() for t in tables])

    if not yes:
        confirm(
            f"You are about to anonymize {total} rows. Are you sure?",
            abort=True,
        )

    fake = Faker()
    fake.seed_instance(0)
    pbar = tqdm("Anonymizing", total=total)
    users = {}
    with pbar:
        for table in tables:
            func = sys.modules[__name__].__dict__[f'_anonymize_{table}']
            func(db, fake, pbar, users)


def _anonymize_user(db, fake, pbar, users):
    emails = {row['email'] for row in db['user'].all()}
    passwd = _hash_password("secret")
    for user in db['user'].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f'{first_name}.{last_name}@example.com'
        email = _ensure_unique_email(email, emails)
        data = {
            'id': user['id'],
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': fake.phone_number(),
            'password': passwd,
            'year_of_birth': None,
        }
        users[user['email']] = data
        db['user'].update(data, ['id'])
        pbar.update(1)


def _anonymize_representative(db, fake, pbar, users):
    emails = {row['email'] for row in db['representative'].all()}
    for rep in db['representative'].all():
        user = users.get(rep['email'])
        if user:
            first_name = user['first_name']
            last_name = user['last_name']
            email = user['email']
            phone = user['phone']
        else:
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f'{first_name}.{last_name}@example.com'
            email = _ensure_unique_email(email, emails)
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


def _anonymize_old_passwrod(db, fake, pbar, users):
    passwd = _hash_password("secret")
    for user in db['old_password'].all():
        data = {
            'id': user['id'],
            'password': passwd,
        }
        db['old_password'].update(data, ['id'])
        pbar.update(1)


def _anonymize_password_reset_token(db, fake, pbar, users):
    token = str(uuid.uuid4())
    for user in db['password_reset_token'].all():
        data = {
            'id': user['id'],
            'token': token,
        }
        db['password_reset_token'].update(data, ['id'])
        pbar.update(1)


def _anonymize_newsletter_subscription(db, fake, pbar, users):
    emails = {row['email'] for row in db['newsletter_subscription'].all()}
    for row in db['newsletter_subscription'].all():
        if row['email'] and '@' in row['email']:
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f'{first_name}.{last_name}@example.com'
            email = _ensure_unique_email(email, emails)
        else:
            email = row['email']
        data = {
            'id': row['id'],
            'email': email,
        }
        db['newsletter_subscription'].update(data, ['id'])
        pbar.update(1)


def _anonymize_partner_application(db, fake, pbar, users):
    emails = {row['email'] for row in db['partner_application'].all()}
    for row in db['partner_application'].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f'{first_name}.{last_name}@example.com'
        email = _ensure_unique_email(email, emails)
        data = {
            'id': row['id'],
            'email': email,
            'phone': fake.phone_number(),
            'viisp_first_name': first_name,
            'viisp_last_name': last_name,
            'viisp_email': email,
            'viisp_phone': fake.phone_number() if row['viisp_phone'] else None,
            'viisp_dob': None,
        }
        db['partner_application'].update(data, ['id'])
        pbar.update(1)


def _anonymize_sso_token(db, fake, pbar, users):
    for user in db['sso_token'].all():
        data = {
            'id': user['id'],
            'ip': '127.0.0.1',
            'token': str(uuid.uuid4()),
        }
        db['sso_token'].update(data, ['id'])
        pbar.update(1)


def _anonymize_suggestion(db, fake, pbar, users):
    emails = {row['email'] for row in db['suggestion'].all()}
    for row in db['suggestion'].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f'{first_name}.{last_name}@example.com'
        email = _ensure_unique_email(email, emails)
        data = {
            'id': row['id'],
            'email': email,
            'name': f'{first_name} {last_name}',
            'body': fake.sentence(12),
        }
        db['suggestion'].update(data, ['id'])
        pbar.update(1)


def _anonymize_comment(db, fake, pbar, users):
    for row in db['comment'].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        data = {
            'id': row['id'],
            'author_name': f"{first_name} {last_name}",
            'ip_address': '127.0.0.1',
            'body': fake.sentence(12),
        }
        db['comment'].update(data, ['id'])
        pbar.update(1)


def _anonymize_request_event(db, fake, pbar, users):
    for row in db['request_event'].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        data = {
            'id': row['id'],
            'meta': f"{first_name} {last_name}",
        }
        db['request_event'].update(data, ['id'])
        pbar.update(1)


def _ensure_unique_email(
    email: str,
    emails: Set[str],
) -> str:
    num = 0
    unique = email
    while unique in emails:
        num += 1
        unique = email.replace('@', f'{num}@')
    emails.add(unique)
    return unique


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt(10)
    return bcrypt.hashpw('test'.encode(), salt).decode('ascii')


if __name__ == '__main__':
    run(main)
