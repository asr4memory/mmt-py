from django.core.exceptions import ValidationError
from django.test import TestCase

from account.forms import validate_username


class ValidateUsernameTestCase(TestCase):
    def test_too_long(self):
        """Raises if username is too long"""
        self.assertRaises(
            ValidationError, validate_username, "hello_this_is_a_nice_username"
        )

    def test_too_short(self):
        """Raises if username is too short"""
        self.assertRaises(ValidationError, validate_username, "mac")

    def test_incorrect_format(self):
        """Raises if username has an incorrect format"""
        self.assertRaises(ValidationError, validate_username, "max headroom")
        self.assertRaises(ValidationError, validate_username, "Max Headroom")
        self.assertRaises(ValidationError, validate_username, "max2 headroom")
        self.assertRaises(ValidationError, validate_username, "max headroom.")

    def test_correct_format(self):
        """Does not raise if username has correct format"""
        self.assertIsNone(validate_username("exa_alice"))
