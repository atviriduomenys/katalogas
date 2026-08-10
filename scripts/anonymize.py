import json
import sys
import uuid
from typing import Set

import dataset
from dataset import Database, Table
from faker import Faker
from tqdm import tqdm
from typer import Argument, Option, confirm, run


_KEEP_PUBLIC_CONTENT = False


def main(
    uri: str = Argument(..., help=("Database URI (postgresql://user:pass@host:port/db)")),
    yes: bool = Option(False, help="Do not ask anything, just do it"),
    keep_public_content: bool = Option(
        False,
        help=(
            "Keep already published editorial content readable: news and CMS page texts, "
            "titles and slugs. Personal data is still anonymized everywhere, including the "
            "news byline (news_item.author_name). Use this when someone has to REVIEW the "
            "content, e.g. after a CMS migration - with everything replaced by 'example' "
            "such a review proves nothing."
        ),
    ),
):
    """
    Anonymize database.

    WARNING! This command will modify database data, without possibility to
    restore it. So before using this command, make sure to pass correct database
    connection string.
    """
    global _KEEP_PUBLIC_CONTENT
    _KEEP_PUBLIC_CONTENT = keep_public_content

    db = dataset.connect(uri)

    tables = (
        "organization",
        "adp_cms_page",
        "news_item",
        "post_content",
        "reversion_version",
        "api_description",
        "vitrina_datasets_contact",
        "open_data_dov_lt",
        "hitcount_hit",
        "harvesting_result",
        "django_session",
        "dataset_resource_migrate",
        "dataset_resource",
        "dataset_migrate",
        "dataset",
        "cms_page",
        "account_emailconfirmation",
        "socialaccount_socialaccount",
        "socialaccount_socialtoken",
        "socialaccount_socialapp",
        "django_admin_log",
        "sent_mail",
        "contact",
        "vitrina_uapi_agent",
        "viispkey",
        "viisptokenkey",
        "user_email_device",
        "account_emailaddress",
        "otp_email_emaildevice",
        "representative_request",
        "api_key",
        "user",
        "representative",
        "old_password",
        "password_reset_token",
        "newsletter_subscription",
        "partner_application",
        "sso_token",
        "suggestion",
        "comment",
        "request_event",
    )

    total = sum([db[_table_for(db, t)].count() for t in tables])

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
            func = sys.modules[__name__].__dict__[f"_anonymize_{table}"]
            func(db, fake, pbar, users)


def _table_for(db: Database, name: str) -> str:
    """Map a logical name to the table that actually holds the data.

    After the django-cms 5 upgrade the `djangocms_blog_*` tables are gone and the
    content lives in `djangocms_stories_*`. The field names are identical, only the
    table differs. The script has to work both before and after the upgrade,
    otherwise the first dump taken after the upgrade would have no working
    anonymization.
    """
    if name == "post_content":
        if "djangocms_stories_postcontent" in db.tables:
            return "djangocms_stories_postcontent"
        return "djangocms_blog_post_translation"
    return name


def _anonymize_organization(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["organization"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.address(),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_post_content(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db[_table_for(db, "post_content")]
    pk_name = "id"
    if _KEEP_PUBLIC_CONTENT:
        # The news texts are already published publicly, and this table holds no
        # personal data: the author is a foreign key to a user, and users are
        # anonymized separately.
        pbar.update(objects.count())
        return
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "title": "example",
            "slug": f"example-{uuid.uuid4()}",
            "abstract": "<p>example</p>",
            "meta_description": "example",
            "meta_title": "example",
            "meta_keywords": "example",
            "subtitle": "<p>example</p>",
            "post_text": "<p>example</p>",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_news_item(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["news_item"]
    pk_name = "id"
    for record in objects.all():
        if _KEEP_PUBLIC_CONTENT:
            # Keep the text, but not the byline: the article is public, the
            # person's name is still personal data.
            data = {pk_name: record[pk_name], "author_name": "example, example"}
        else:
            data = {
                pk_name: record[pk_name],
                "body": "<p>example</p>",
                "title": "example",
                "slug": f"example-{uuid.uuid4()}",
                "summary": "example",
                "author_name": "example, example",
            }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_adp_cms_page(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["adp_cms_page"]
    pk_name = "id"
    if _KEEP_PUBLIC_CONTENT:
        # The legacy CMS page texts are public and the table holds no personal data.
        pbar.update(objects.count())
        return
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "body": "<p>example</p>",
            "title": "example",
            "description": "example",
            "slug": f"example-{uuid.uuid4()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_reversion_version(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["reversion_version"]
    pk_name = "id"
    for record in objects.all():
        data = {pk_name: record[pk_name], "serialized_data": ""}
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_api_description(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["api_description"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "contact_email": fake.email(),
            "contact_name": fake.first_name(),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_vitrina_datasets_contact(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["vitrina_datasets_contact"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "email": fake.email(),
            "phone": fake.phone_number(),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_open_data_dov_lt(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["open_data_dov_lt"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "contact_info": f"Example, {fake.first_name()}, {fake.last_name()}, {fake.email()}, {fake.phone_number()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_hitcount_hit(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["hitcount_hit"]
    pk_name = "id"
    for record in objects.all():
        data = {pk_name: record[pk_name], "ip": "127.0.0.1", "session": "example-session-hash"}
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_harvesting_result(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["harvesting_result"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "raw_data": '<?xml version="1.0" encoding="UTF-8"?><root></root>',
            "remote_id": f"example-{uuid.uuid4()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_django_session(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["django_session"]
    no_objects_to_delete = objects.count()
    objects.delete()  # Keeping not safe, editing will break things.
    pbar.update(no_objects_to_delete)


def _anonymize_dataset_resource(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["dataset_resource"]
    pk_name = "id"
    for record in objects.all():
        data = {pk_name: record[pk_name], "url": fake.url()}
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_dataset_resource_migrate(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["dataset_resource_migrate"]
    pk_name = "id"
    for record in objects.all():
        data = {pk_name: record[pk_name], "url": fake.url()}
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_dataset_migrate(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["dataset_migrate"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "meta": json.dumps({}),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_dataset(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["dataset"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "meta": json.dumps({}),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_cms_page(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["cms_page"]
    pk_name = "id"
    for record in objects.all():
        data = {pk_name: record[pk_name], "changed_by": fake.first_name(), "created_by": fake.first_name()}
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_account_emailconfirmation(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["account_emailconfirmation"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "key": f"example-key-{uuid.uuid4()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_socialaccount_socialtoken(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["socialaccount_socialtoken"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "token_secret": f"example-secret-{uuid.uuid4()}",
            "token": "example-token",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_socialaccount_socialapp(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["socialaccount_socialapp"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "secret": f"example-{uuid.uuid4()}",
            "client_id": "example-client_id",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_socialaccount_socialaccount(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["socialaccount_socialaccount"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "extra_data": json.dumps(
                {
                    "personal_code": "example-hashed-code",
                    "coordinator_phone_number": None,
                    "coordinator_email": fake.email(domain="example.com"),
                    "password_not_set": False,
                }
            ),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_django_admin_log(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["django_admin_log"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "object_repr": f"{fake.first_name()} {fake.last_name()}",
            "change_message": [],
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_sent_mail(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["sent_mail"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "recipient": [_email_plus_uuid(fake)],
            "email_content": "<p>Email content example</p>",
            "email_subject": "Example email subject",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_otp_email_emaildevice(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["otp_email_emaildevice"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "email": _email_plus_uuid(fake),
            "name": f"{fake.first_name()} {fake.last_name()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_api_key(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["api_key"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "api_key": f"example-{uuid.uuid4()}",
            "client_id": f"example-{uuid.uuid4()}",
            "client_name": f"example-{uuid.uuid4()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_representative_request(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["representative_request"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "email": _email_plus_uuid(fake),
            "phone": fake.phone_number(),
            "document": "path/to/example.docx",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_account_emailaddress(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["account_emailaddress"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "email": _email_plus_uuid(fake),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_user_email_device(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["user_email_device"]
    pk_name = "emaildevice_ptr_id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "ip_address": "127.0.0.1",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_viisptokenkey(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["viisptokenkey"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "key_content": f"example-{uuid.uuid4()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_viispkey(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["viispkey"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "key_content": f"example-{uuid.uuid4()}",
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_vitrina_uapi_agent(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    objects: Table = db["vitrina_uapi_agent"]
    pk_name = "uuid"
    for agent in objects.all():
        data = {pk_name: agent[pk_name], "oauth_client_id": uuid.uuid4()}
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_contact(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["contact"]
    pk_name = "id"
    for contact in objects.all():
        data = {
            pk_name: contact[pk_name],
            "email": _email_plus_uuid(fake),
            "phone": fake.phone_number(),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_user(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    passwd = _get_unusable_password()
    for user in db["user"].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = _email_plus_uuid(fake)
        data = {
            "id": user["id"],
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": fake.phone_number(),
            "password": passwd,
            "year_of_birth": None,
        }
        users[user["email"]] = data
        db["user"].update(data, ["id"])
        pbar.update(1)


def _anonymize_representative(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    for rep in db["representative"].all():
        user = users.get(rep["email"])
        if user:
            first_name = user["first_name"]
            last_name = user["last_name"]
            email = user["email"]
            phone = user["phone"]
        else:
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = _email_plus_uuid(fake)
            phone = fake.phone_number()
        data = {
            "id": rep["id"],
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
        }
        db["representative"].update(data, ["id"])
        pbar.update(1)


def _anonymize_old_password(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    passwd = _get_unusable_password()
    for user in db["old_password"].all():
        data = {
            "id": user["id"],
            "password": passwd,
        }
        db["old_password"].update(data, ["id"])
        pbar.update(1)


def _anonymize_password_reset_token(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    token = str(uuid.uuid4())
    for user in db["password_reset_token"].all():
        data = {
            "id": user["id"],
            "token": token,
        }
        db["password_reset_token"].update(data, ["id"])
        pbar.update(1)


def _anonymize_newsletter_subscription(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    for row in db["newsletter_subscription"].all():
        if row["email"] and "@" in row["email"]:
            email = _email_plus_uuid(fake)
        else:
            email = row["email"]
        data = {
            "id": row["id"],
            "email": email,
        }
        db["newsletter_subscription"].update(data, ["id"])
        pbar.update(1)


def _anonymize_partner_application(
    db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]
) -> None:
    for row in db["partner_application"].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = _email_plus_uuid(fake)
        data = {
            "id": row["id"],
            "email": email,
            "phone": fake.phone_number(),
            "viisp_first_name": first_name,
            "viisp_last_name": last_name,
            "viisp_email": email,
            "viisp_phone": fake.phone_number() if row["viisp_phone"] else None,
            "viisp_dob": None,
        }
        db["partner_application"].update(data, ["id"])
        pbar.update(1)


def _anonymize_sso_token(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    for user in db["sso_token"].all():
        data = {
            "id": user["id"],
            "ip": "127.0.0.1",
            "token": str(uuid.uuid4()),
        }
        db["sso_token"].update(data, ["id"])
        pbar.update(1)


def _anonymize_suggestion(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    for row in db["suggestion"].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = _email_plus_uuid(fake)
        data = {
            "id": row["id"],
            "email": email,
            "name": f"{first_name} {last_name}",
            "body": fake.sentence(12),
        }
        db["suggestion"].update(data, ["id"])
        pbar.update(1)


def _anonymize_comment(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    for row in db["comment"].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        data = {
            "id": row["id"],
            "author_name": f"{first_name} {last_name}",
            "ip_address": "127.0.0.1",
            "body": fake.sentence(12),
        }
        db["comment"].update(data, ["id"])
        pbar.update(1)


def _anonymize_request_event(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    for row in db["request_event"].all():
        first_name = fake.first_name()
        last_name = fake.last_name()
        data = {
            "id": row["id"],
            "meta": f"{first_name} {last_name}",
        }
        db["request_event"].update(data, ["id"])
        pbar.update(1)


def _ensure_unique_email(
    email: str,
    emails: Set[str],
) -> str:
    num = 0
    unique = email
    while unique in emails:
        num += 1
        unique = email.replace("@", f"{num}@")
    emails.add(unique)
    return unique


def _email_plus_uuid(fake) -> str:
    return f"{fake.user_name()}.{uuid.uuid4().hex[:10]}@example.com"


def _get_unusable_password() -> str:
    UNUSABLE_PASSWORD_PREFIX = "!"  # This will never be a valid encoded hash
    return f"{UNUSABLE_PASSWORD_PREFIX}{uuid.uuid4()}"


if __name__ == "__main__":
    run(main)
