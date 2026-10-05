# Loads the Celery app whenever Django starts, so that tasks sent from the web
# process use the CELERY_* settings, among them the task routes.
from .celery import app as celery_app

__all__ = ('celery_app',)
