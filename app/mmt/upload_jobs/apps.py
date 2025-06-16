from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UploadJobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mmt.upload_jobs"
    verbose_name = _("Upload jobs")
