from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from mmt.core.utils import format_duration

register = template.Library()


@register.filter
def status_label(value: str) -> str:
    labels = {
        'missing': _('Missing'),
        'incomplete': _('Incomplete'),
        'processing': _('Processing'),
        'complete': _('Complete'),
    }
    return labels.get(value, value)


@register.filter
def duration(value: float) -> str:
    """Django template filter that formats media duration."""
    return format_duration(value)


@register.simple_tag
def recent_upload_activity() -> bool:
    from mmt.uploaded_files.models import UploadedFile

    since = timezone.now() - timedelta(minutes=5)
    return UploadedFile.objects.filter(updated_at__gte=since).exists()
