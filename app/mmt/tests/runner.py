import warnings

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class MMTTestRunner(DiscoverRunner):
    def run_tests(self, *args, **kwargs):
        # Show all warnings once, especially to show DeprecationWarning
        # messages which Python ignores by default
        warnings.simplefilter("default")

        with override_settings(**TEST_SETTINGS):
            return super().run_tests(*args, **kwargs)

TEST_SETTINGS = {
    "PAGINATION_COUNT": 10,
}
