from django import template
from django.utils.translation import gettext_lazy as _

from mmt.core.media_types import MediaKind, media_kind

register = template.Library()


@register.filter
def category_label(media_type: str) -> str:
    """Return the display label of the category of a MIME type."""
    kind = media_kind(media_type)
    if kind == MediaKind.VIDEO:
        return _('Video')
    if kind == MediaKind.AUDIO:
        return _('Audio')
    if kind == MediaKind.IMAGE:
        return _('Image')
    if media_type == 'application/pdf':
        return _('PDF')
    if media_type.startswith('text/'):
        return _('Text')
    return _('Other')
