#!/bin/sh

. /app/bin/activate
cd /app/django-app
python manage.py check
python manage.py compilemessages
python manage.py collectstatic --noinput
python manage.py migrate

exec "$@"
