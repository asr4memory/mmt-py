#!/bin/sh

# if [ "$DATABASE" = "postgres" ]
# then
#     echo "Waiting for postgres..."

#     while ! nc -z $SQL_HOST $SQL_PORT; do
#       sleep 0.1
#     done

#     echo "PostgreSQL started"
# fi

source /app/bin/activate
cd /app/django-app
npm run build
python manage.py collectstatic --noinput
python manage.py compilemessages # Affects image
python manage.py migrate

exec "$@"
