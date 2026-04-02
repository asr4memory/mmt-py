from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mmt.my_account'
    verbose_name = _('Account')

    def ready(self):
        version = getattr(settings, 'MMT_TERMS_VERSION', None)
        if version is None:
            raise ImproperlyConfigured('MMT_TERMS_VERSION is not set in settings.')
        if not isinstance(version, int) or version <= 0:
            raise ImproperlyConfigured('MMT_TERMS_VERSION must be a positive integer.')
