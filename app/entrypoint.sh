#!/bin/sh

# if [ "$DATABASE" = "postgres" ]
# then
#     echo "Waiting for postgres..."

#     while ! nc -z $SQL_HOST $SQL_PORT; do
#       sleep 0.1
#     done

#     echo "PostgreSQL started"
# fi

. /app/bin/activate
cd /app/django-app
python manage.py check
python manage.py compilemessages
python manage.py collectstatic --noinput
python manage.py migrate

exec "$@"
