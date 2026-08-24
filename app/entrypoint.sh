#!/bin/sh

. /app/bin/activate
cd /app/django-app

# Prepare Django. Translations and static files are baked in at build time;
# only the database steps remain here since they need a live connection.
python manage.py migrate
python manage.py creategroups

echo "Container started, handing off to: $*"
exec "$@"
