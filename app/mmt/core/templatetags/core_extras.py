from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def file_category_label(value: str) -> str:
    labels = {
        'video': _('Video'),
        'audio': _('Audio'),
        'pdf': _('PDF'),
        'image': _('Image'),
        'text': _('Text'),
    }
    return labels.get(value, value)
