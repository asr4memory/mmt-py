from django.core.exceptions import ValidationError
from django.test import TestCase

from account.forms import validate_username


class ValidateUsernameTestCase(TestCase):
    def test_too_long(self):
        """Raises if username is too long"""
        self.assertRaisesMessage(
            ValidationError,
            "hello_this_is_a_nice_username is too long",
            validate_username,
            "hello_this_is_a_nice_username",
        )

    def test_too_short(self):
        """Raises if username is too short"""
        self.assertRaisesMessage(ValidationError, "mac is too short", validate_username, "mac")

    def test_incorrect_format(self):
        """Raises if username has an incorrect format"""
        message = "does not have the right format"
        self.assertRaisesMessage(ValidationError, message, validate_username, "max headroom")
        self.assertRaisesMessage(ValidationError, message, validate_username, "Max Headroom")
        self.assertRaisesMessage(ValidationError, message, validate_username, "max2 head")
        self.assertRaisesMessage(ValidationError, message, validate_username, "max head.")

    def test_correct_format(self):
        """Does not raise if username has correct format"""
        self.assertIsNone(validate_username("exa_alice"))
