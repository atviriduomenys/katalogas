#!/bin/bash
echo "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
echo "RUN_MODE=$RUN_MODE"

python3 manage.py collectstatic --noinput
python3 manage.py migrate -v 2 || exit 1
python3 manage.py rebuild_index --noinput --using default
python3 manage.py compilemessages
export DJANGO_SUPERUSER_EMAIL=test@test.com; export DJANGO_SUPERUSER_USERNAME=test@test.com; export DJANGO_SUPERUSER_PASSWORD=test; python manage.py createsuperuser --noinput || True

cd webpack
npm run build || echo "⚠️ Webpack build (partially) failed, continuing..."
cd ..

if [[ $RUN_MODE == "DEVELOPMENT" ]]; then
  python3 manage.py runserver 0.0.0.0:8000
else
  gunicorn -b 0.0.0.0:8000 vitrina.wsgi:application --log-file=-
fi

