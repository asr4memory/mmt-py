#!/bin/sh

. /app/bin/activate
cd /app/django-app

# Make upload temp directory if it does not exist.
mkdir -p user_files/_tmp

# Prepare Django
python manage.py check
python manage.py compilemessages --verbosity 0
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py creategroups

echo "Container started, handing off to: $*"
exec "$@"
