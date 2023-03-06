# Install all dependencies
poetry install

# Run tests
poetry run pytest -vvxra --tb=short --no-migrations tests

# Run migrations
poetry run python manage.py migrate

# Static files
poetry run python manage.py collectstatic
(cd webpack && npm install && npm run build)

# Run dev server
poetry run python manage.py runserver

# Anonymize production data
poetry run python scripts/anonymize.py postgresql://adp:secret@127.0.0.1:5432/adp-dev
pg_dump -Fc -h localhost -U adp adp-dev > var/postgres_adp-dev_anonymized.dump
pg_restore -Fc -h localhost -U adp -d adp-dev < postgres_adp-dev_anonymized.dump


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
