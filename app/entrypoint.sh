#!/bin/sh

. /app/bin/activate
cd /app/django-app
python manage.py check
python manage.py compilemessages --verbosity 0
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py creategroups

exec "$@"
