#!/bin/bash
echo "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
echo "RUN_MODE=$RUN_MODE"

cd webpack
npm run build || echo "⚠️ Webpack build (partially) failed, continuing..."
cd ..

python3 manage.py collectstatic --noinput
# --skip-checks bypasses the URL system check that queries the Site table before migrations run,
# which causes Site.DoesNotExist on a fresh database (django-cms bootstrapping issue).
python3 manage.py migrate --skip-checks -v 2 || exit 1
python3 manage.py rebuild_index --noinput --using default
export DJANGO_SUPERUSER_EMAIL=test@test.com; export DJANGO_SUPERUSER_USERNAME=test@test.com; export DJANGO_SUPERUSER_PASSWORD=test; python manage.py createsuperuser --noinput || True

if [[ $RUN_MODE == "DEVELOPMENT" ]]; then
  python3 manage.py runserver 0.0.0.0:8000
else
  gunicorn -b 0.0.0.0:8000 vitrina.wsgi:application --log-file=-
fi

