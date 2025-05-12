#!/bin/sh

echo "Waiting for MariaDB..."
while ! nc -z db 3306; do
  sleep 0.1
done
echo "MariaDB started"

. /app/bin/activate
cd /app/django-app
python manage.py check
python manage.py compilemessages
python manage.py collectstatic --noinput
python manage.py migrate

exec "$@"
