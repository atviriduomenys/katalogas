import json
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Set

import dataset
from dataset import Database, Table
from faker import Faker
from tqdm import tqdm
from typer import Argument, Option, confirm, echo, run


# The djangocms-blog schema is gone; only an upgrade that stopped half way leaves it standing.
STORY_CONTENT_TABLE = "djangocms_stories_postcontent"
LEGACY_STORY_TABLE = "djangocms_blog_post_translation"

# Their rows are still walked with --keep-public-content: drafts are scrubbed, and so are bylines in kept text.
PUBLIC_CONTENT_TABLES = (STORY_CONTENT_TABLE, "news_item", "adp_cms_page")


def _story_content_table(db: Database) -> str:
    """The story content table, or stop: `dataset` would silently scrub a missing one.

    A pre-upgrade or half-upgraded database is refused too - its legacy text would go out as is.
    """
    if STORY_CONTENT_TABLE not in db.tables:
        raise SystemExit(
            f"This database has no {STORY_CONTENT_TABLE}. Story text would go out unscrubbed, so nothing was changed."
        )
    if LEGACY_STORY_TABLE in db.tables:
        raise SystemExit(
            f"This database still has {LEGACY_STORY_TABLE}, left by a django-cms 5 upgrade that did "
            "not finish. This script only scrubs the djangocms-stories schema, so that text would go "
            "out as it is - nothing was changed."
        )
    return STORY_CONTENT_TABLE


def main(
    uri: str = Argument(..., help=("Database URI (postgresql://user:pass@host:port/db)")),
    yes: bool = Option(False, help="Do not ask anything, just do it"),
    keep_public_content: bool = Option(
        False,
        help=(
            "Keep PUBLISHED editorial content readable: stories, news and old portal pages - "
            "their texts, titles and slugs. Drafts, scheduled, expired, non-public and deleted rows are anonymized "
            "as usual - only what the site already shows to everyone is spared. Bylines are "
            "removed, including the one the old news migration wrote into the article text as "
            "'<p>Autorius: NAME</p>'. WARNING: the kept text itself is NOT scanned, so it can "
            "still contain names, e-mail addresses or phone numbers that an editor typed into "
            "an article. Use this when someone has to REVIEW the content, e.g. after a CMS "
            "migration - with every article replaced by 'example' such a review proves nothing."
        ),
    ),
):
    """
    Anonymize database.

    WARNING! This command will modify database data, without possibility to
    restore it. So before using this command, make sure to pass correct database
    connection string.
    """
    if keep_public_content:
        echo(
            "WARNING! --keep-public-content leaves published article and page text as it is. "
            "That text is not scanned, so it can still hold names, e-mail addresses or phone "
            "numbers an editor typed in. Do not treat such a dump as fully anonymized."
        )

    db = dataset.connect(uri)

    tables = (
        "organization",
        "adp_cms_page",
        "news_item",
        _story_content_table(db),
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
        *(["cms_pagecontent"] if "cms_pagecontent" in db.tables else []),
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
            func = sys.modules[__name__].__dict__[f"_anonymize_{table}"]
            if keep_public_content and table in PUBLIC_CONTENT_TABLES:
                func(db, fake, pbar, users, keep_public_content=True)
            else:
                func(db, fake, pbar, users)

    _scrub_story_plugins(db, _published_story_content_ids(db) if keep_public_content else set())


# The old news migration (scripts/migrate_news.py, now in git history) prepended "<p>Autorius: NAME</p>"
# to the body and the summary, so the byline sits inside post_text / abstract too. Keeping the
# article text therefore means keeping that name unless it is scrubbed out explicitly.
_BYLINE_RE = re.compile(r"<p>Autorius:.*?</p>", re.S)


def _scrub_byline(text: str | None) -> str | None:
    if not text:
        return text
    return _BYLINE_RE.sub("<p>Autorius: example, example</p>", text)


def _published_story_content_ids(db: Database) -> Set[int]:
    """Ids of story contents the site shows: a published version of a post inside its publication window.

    Drafts, unpublished and archived versions, scheduled and expired posts are not public, so their text is not spared.
    """
    if "djangocms_versioning_version" not in db.tables:
        return set()

    now = datetime.now(timezone.utc)

    def _passed(value, future: bool) -> bool:
        if value is None:
            return True
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value > now if future else value <= now

    published_versions = {
        row["object_id"]
        for row in db.query(
            """
            SELECT version.object_id
            FROM djangocms_versioning_version version
            JOIN django_content_type ct ON ct.id = version.content_type_id
            WHERE ct.app_label = 'djangocms_stories' AND ct.model = 'postcontent' AND version.state = 'published'
            """
        )
    }
    public_posts = {
        row["id"]
        for row in db["djangocms_stories_post"].all()
        if _passed(row.get("date_published"), future=False) and _passed(row.get("date_published_end"), future=True)
    }
    return {
        row["id"]
        for row in db[STORY_CONTENT_TABLE].all()
        if row["id"] in published_versions and row.get("post_id") in public_posts
    }


def _anonymize_organization(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["organization"]
    pk_name = "id"
    for record in objects.all():
        data = {
            pk_name: record[pk_name],
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.address(),
            "website": fake.url(),
        }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_story_content(db: Database, pbar: tqdm, table: str, keep_public_content: bool = False) -> None:
    objects: Table = db[table]
    pk_name = "id"
    published = _published_story_content_ids(db) if keep_public_content else set()
    for record in objects.all():
        if record[pk_name] in published:
            # Published article: keep the text, but strip the byline embedded in it.
            objects.update(
                {
                    pk_name: record[pk_name],
                    "post_text": _scrub_byline(record.get("post_text")),
                    "abstract": _scrub_byline(record.get("abstract")),
                },
                [pk_name],
            )
            pbar.update(1)
            continue
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


# Empty unless a stories config has use_placeholder on (STORIES_USE_PLACEHOLDER is off
# by default); such a config renders its article text from here instead of post_text.
STORY_CONTENT_TYPES = (("djangocms_stories", "postcontent"),)


def _scrub_story_plugins(db: Database, kept_content_ids: Set[int] = frozenset()) -> None:
    """Scrub story text plugins; those of kept story contents only lose their byline."""
    if "djangocms_text_text" not in db.tables:
        return

    conditions = " OR ".join(
        f"(ct.app_label = '{app_label}' AND ct.model = '{model}')" for app_label, model in STORY_CONTENT_TYPES
    )
    rows = db.query(
        f"""
        SELECT txt.cmsplugin_ptr_id, txt.body, placeholder.object_id
        FROM djangocms_text_text txt
        JOIN cms_cmsplugin plugin ON plugin.id = txt.cmsplugin_ptr_id
        JOIN cms_placeholder placeholder ON placeholder.id = plugin.placeholder_id
        JOIN django_content_type ct ON ct.id = placeholder.content_type_id
        WHERE {conditions}
        """
    )
    texts: Table = db["djangocms_text_text"]
    for row in list(rows):
        body = _scrub_byline(row["body"]) if row["object_id"] in kept_content_ids else "<p>example</p>"
        texts.update({"cmsplugin_ptr_id": row["cmsplugin_ptr_id"], "body": body}, ["cmsplugin_ptr_id"])


def _anonymize_djangocms_stories_postcontent(
    db: Database,
    fake: Faker,
    pbar: tqdm,
    users: dict[str, dict[str, str | None]],
    keep_public_content: bool = False,
) -> None:
    """Story text."""
    _anonymize_story_content(db, pbar, STORY_CONTENT_TABLE, keep_public_content)


def _anonymize_news_item(
    db: Database,
    fake: Faker,
    pbar: tqdm,
    users: dict[str, dict[str, str | None]],
    keep_public_content: bool = False,
) -> None:
    objects: Table = db["news_item"]
    pk_name = "id"
    for record in objects.all():
        if keep_public_content and record.get("is_public") and not record.get("deleted"):
            # Published item: keep the text, drop both byline columns and the byline
            # that the old news migration wrote into the text itself.
            data = {
                pk_name: record[pk_name],
                "author_name": "example, example",
                "author": None,  # bytea in production, text in the canonical schema - None fits both
                "body": _scrub_byline(record.get("body")),
                "summary": _scrub_byline(record.get("summary")),
            }
        else:
            data = {
                pk_name: record[pk_name],
                "body": "<p>example</p>",
                "title": "example",
                "slug": f"example-{uuid.uuid4()}",
                "summary": "example",
                "author_name": "example, example",
                "author": None,  # bytea in production, text in the canonical schema - None fits both
            }
        objects.update(data, [pk_name])
        pbar.update(1)


def _anonymize_adp_cms_page(
    db: Database,
    fake: Faker,
    pbar: tqdm,
    users: dict[str, dict[str, str | None]],
    keep_public_content: bool = False,
) -> None:
    objects: Table = db["adp_cms_page"]
    pk_name = "id"
    for record in objects.all():
        if keep_public_content and record.get("published") and not record.get("deleted"):
            pbar.update(1)
            continue
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


def _anonymize_cms_pagecontent(db: Database, fake: Faker, pbar: tqdm, users: dict[str, dict[str, str | None]]) -> None:
    objects: Table = db["cms_pagecontent"]
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
