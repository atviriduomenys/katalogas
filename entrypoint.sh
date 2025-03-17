#!/bin/bash
echo "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
echo "RUN_MODE=$RUN_MODE"

python3 manage.py collectstatic --noinput
python3 manage.py migrate -v 2 || exit 1

cd webpack
npm run build || echo "⚠️ Webpack build (partially) failed, continuing..."
cd ..

if [[ $RUN_MODE == "DEVELOPMENT" ]]; then
  python3 manage.py runserver 0.0.0.0:8000
else
  gunicorn -b 0.0.0.0:8000 -c /app/conf/gunicorn.conf.aws.py wsgi:application --log-file=-
fi
