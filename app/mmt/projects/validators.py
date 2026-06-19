from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from mmt.core.utils import filename_safe


def validate_filename_safe(value):
    try:
        filename_safe(value)
    except ValueError:
        raise ValidationError(
            _(
                'This title cannot be used as a project name. Please use letters or numbers.'
            )
        )
