from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .validators import validate_username

User = get_user_model()


def test_validator_works():
    assert validate_username("alice-henderson") is None
