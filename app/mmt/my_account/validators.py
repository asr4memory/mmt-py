import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


username_format = re.compile(r"^[a-z]+_[a-z0-9]+$")


def validate_username(value):
    if len(value) < 4:
        raise ValidationError(
            _("%(value)s is too short"),
            params={"value": value},
        )
    if len(value) > 12:
        raise ValidationError(
            _("%(value)s is too long"),
            params={"value": value},
        )
    if not username_format.match(value):
        raise ValidationError(
            _("%(value)s does not have the right format"),
            params={"value": value},
        )


custom_username_validators = [validate_username]
