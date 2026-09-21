#!/bin/bash
echo "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
echo "RUN_MODE=$RUN_MODE"

cd webpack
npm run build || echo "⚠️ Webpack build (partially) failed, continuing..."
cd ..

python3 manage.py collectstatic --noinput
# Refuses a database the django-cms 4.1 migration tool has not finished, then migrates.
# Temporary: #2795 goes back to a plain migrate once every environment is upgraded.
./scripts/migrate_djangocms.sh || exit 1
python3 manage.py rebuild_search
export DJANGO_SUPERUSER_EMAIL=test@test.com; export DJANGO_SUPERUSER_USERNAME=test@test.com; export DJANGO_SUPERUSER_PASSWORD=test; python manage.py createsuperuser --noinput || True

if [[ $RUN_MODE == "DEVELOPMENT" ]]; then
  python3 manage.py runserver 0.0.0.0:8000
else
  gunicorn -b 0.0.0.0:8000 vitrina.wsgi:application --log-file=-
fi
