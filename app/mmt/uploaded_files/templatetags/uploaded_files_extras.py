from django import template

from mmt.core.utils import format_duration

register = template.Library()


@register.filter
def duration(value: float) -> str:
    """Django template filter that formats media duration."""
    return format_duration(value)
