from django import template
from django.utils.translation import gettext_lazy as _

from mmt.core.media_types import Category, category

register = template.Library()


@register.filter
def category_label(media_type: str) -> str:
    """Return the display label of the category of a MIME type."""
    labels = {
        Category.VIDEO: _('Video'),
        Category.AUDIO: _('Audio'),
        Category.PDF: _('PDF'),
        Category.IMAGE: _('Image'),
        Category.TEXT: _('Text'),
        Category.OTHER: _('Other'),
    }
    return labels[category(media_type)]
