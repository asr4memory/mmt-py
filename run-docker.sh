#!/bin/bash
docker run \
    -e DJANGO_ENV=production \
    -e SECRET_KEY=secret \
    -e DATABASE_URL=mysql://root:password@localhost/mmt \
    -e EMAIL_URL=smtp:// \
    -e CELERY_BROKER_URL=redis://localhost \
    -it mmt:latest /bin/bash
