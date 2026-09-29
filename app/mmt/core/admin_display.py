from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.text import Truncator


def truncated(text: str, length: int = 60) -> SafeString:
    """Return text shortened to length characters, with the full text as tooltip."""
    return format_html(
        '<span title="{}">{}</span>', text, Truncator(text).chars(length)
    )
