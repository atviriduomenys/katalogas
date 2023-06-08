# Run all services
docker-compose up -d

# Install all dependencies
poetry install

# Run tests
poetry run pytest -vvxra --tb=short --no-migrations tests

# Run migrations
poetry run python manage.py migrate

# Run one time migrations on fresh database dump
poetry run python scripts/migrate_files.py \
    -distribution-path var/data/ \
    --cms-path var/data/files/ \
    --structure-path var/data/structure/
poetry run python scripts/migrate_pages.py
poetry run python scripts/migrate_news.py

# Reset passwords of all users
poetry run python manage.py shell
from vitrina.users.models import User
user = User()
user.set_password('secret')
User.objects.update(password=user.password)
exit()

# Update search index
poetry run python manage.py rebuild_index --noinput --using default

# Static files
poetry run python manage.py collectstatic --noinput
(cd webpack && npm install)
(cd webpack && npm run build)

# Run dev server
test -n "$PID" && kill $PID
poetry run python manage.py runserver --noreload &>> var/vitrina.log &; PID=$!
tail -50 var/vitrina.log


# 2022-12-14 09:54 Check translations

poetry run django-admin makemessages --help
#| --locale LOCALE, -l LOCALE
#|   Creates or updates the message files for the given locale(s) (e.g. pt_BR).
#|   Can be used multiple times.
#| --all, -a
#|   Updates the message files for all existing locales.
poetry run python manage.py makemessages -l en -l lt
poetry run python manage.py makemessages -a
poetry run python manage.py makemessages -av1
#| processing locale en
#| processing locale lt
poetry run python manage.py compilemessages
#| processing file django.po in /home/sirex/dev/data/katalogas/vitrina/locale/en/LC_MESSAGES
#| processing file django.po in /home/sirex/dev/data/katalogas/vitrina/locale/lt/LC_MESSAGES


# 2023-03-07 11:34 Recreate anonymized database dump

# Drop all data in database
docker-compose run -T --rm -e PGPASSWORD=secret postgres \
    psql -h postgres -U adp adp-dev <<EOF
BEGIN TRANSACTION;
  DROP SCHEMA "public" CASCADE;
  CREATE SCHEMA "public";
COMMIT;
EOF

# Load database dump
pg_restore -Fc -h localhost -U adp -d adp-dev < var/postgres_adp.dump

psql -h localhost -U adp -d adp-dev <<EOF
-- Move FK from cms_page to adp_cms_page and drop cms_page,
-- because cms_page is used by Django CMS.
ALTER TABLE "cms_attachment"
    DROP CONSTRAINT "fkb61y6xtsjm3lph7jvqwvna336";
ALTER TABLE ONLY "cms_attachment"
    ADD CONSTRAINT "fkb61y6xtsjm3lph7jvqwvna336"
        FOREIGN KEY (cms_page_id)
        REFERENCES adp_cms_page(id)
        ON UPDATE RESTRICT ON DELETE RESTRICT;
-- Drop duplicate constraint.
ALTER TABLE "cms_attachment"
    DROP CONSTRAINT "fkd24jc8oag6itrip826odio0d";
DROP TABLE "cms_page";
EOF

poetry run python scripts/anonymize.py postgresql://adp:secret@localhost:5432/adp-dev
#| You are about to anonymize 10718 rows. Are you sure? [y/N]: y
y
#| 100% 10718/10718 [00:29<00:00, 359.50it/s]
pg_dump -Fc -h localhost -U adp adp-dev > var/postgres_adp_anonymized.dump
du -sh var/postgres_adp_anonymized.dump
pg_restore -Fc -h localhost -U adp -d adp-dev < postgres_adp_anonymized.dump
