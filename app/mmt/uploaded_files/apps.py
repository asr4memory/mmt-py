from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UploadedFilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mmt.uploaded_files"
    verbose_name = _("Uploaded files")
