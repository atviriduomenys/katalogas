#!/bin/bash
echo "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
echo "RUN_MODE=$RUN_MODE"

cd webpack
npm run build || echo "⚠️ Webpack build (partially) failed, continuing..."
cd ..

python3 manage.py collectstatic --noinput
# The helper runs the one-time legacy blog stage when required, then all migrations.
./scripts/migrate_djangocms.sh || exit 1
python3 manage.py rebuild_search

if [[ $RUN_MODE == "DEVELOPMENT" ]]; then
  python3 manage.py runserver 0.0.0.0:8000
else
  gunicorn -b 0.0.0.0:8000 vitrina.wsgi:application --log-file=-
fi
