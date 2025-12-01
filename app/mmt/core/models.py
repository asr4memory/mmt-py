from django.db import models
from django.utils.translation import gettext_lazy as _


class Notice(models.Model):
    title_en = models.CharField(max_length=255, verbose_name=_("Title (English)"))
    title_de = models.CharField(max_length=255, verbose_name=_("Title (German)"))
    content_en = models.TextField(
        blank=True, default="", verbose_name=_("Content (English)")
    )
    content_de = models.TextField(
        blank=True, default="", verbose_name=_("Content (German)")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("notice")
        verbose_name_plural = _("notices")

    def __repr__(self):
        return f"Notice(title_en='{self.title_en}', title_de='{self.title_de}')"

    def __str__(self):
        return f"{self.title_en} / {self.title_de}"
