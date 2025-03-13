#!/bin/bash
echo $DJANGO_SETTINGS_MODULE

python3 manage.py collectstatic --noinput
python3 manage.py migrate -v 2 || exit 1


  if [[ $RUN_MODE == "DEVELOPMENT" ]]; then
    python3 manage.py runserver 0.0.0.0:8000
  else
		gunicorn -b 0.0.0.0:8000 -c /app/conf/gunicorn.conf.aws.py wsgi:application --log-file=-
  fi