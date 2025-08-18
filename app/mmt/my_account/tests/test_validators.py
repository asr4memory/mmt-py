from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from mmt.my_account.validators import validate_username

User = get_user_model()


class UsernameValidatorTests(TestCase):
    def test_validator_works(self):
        result = validate_username("alice-henderson")
        self.assertIsNone(result)

    def test_too_long(self):
        with self.assertRaises(ValidationError):
            validate_username("hello_this_is_a_nice_username_but_it_is_too_long")

    def test_too_short(self):
        with self.assertRaises(ValidationError):
            validate_username("mac")

    def test_incorrect_format(self):
        with self.assertRaises(ValidationError):
            validate_username("no whitespace")

        with self.assertRaises(ValidationError):
            validate_username("NoUppercase")

        with self.assertRaises(ValidationError):
            validate_username("nospecialchars#!")
