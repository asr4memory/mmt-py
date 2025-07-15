import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from .validators import validate_username

User = get_user_model()


def test_validator_works():
    assert validate_username("alice-henderson") is None


def test_too_long():
    with pytest.raises(ValidationError):
        validate_username("hello_this_is_a_nice_username_but_it_is_too_long")


def test_too_short():
    with pytest.raises(ValidationError):
        validate_username("mac")


def test_incorrect_format():
    with pytest.raises(ValidationError):
        validate_username("no whitespace")

    with pytest.raises(ValidationError):
        validate_username("NoUppercase")

    with pytest.raises(ValidationError):
        validate_username("nospecialchars#!")
