import os
import warnings

from django.conf import settings
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class MMTTestRunner(DiscoverRunner):
    def run_tests(self, *args, **kwargs):
        # Show all warnings once, especially to show DeprecationWarning
        # messages which Python ignores by default
        warnings.simplefilter('default')

        with override_settings(**TEST_SETTINGS):
            return super().run_tests(*args, **kwargs)

    def run_suite(self, suite, **kwargs):
        if os.environ.get('CI'):
            import xmlrunner
            os.makedirs('test-results', exist_ok=True)
            return xmlrunner.XMLTestRunner(
                output='test-results',
                verbosity=self.verbosity,
            ).run(suite)
        return super().run_suite(suite, **kwargs)


TEST_SETTINGS = {
    'PAGINATION_COUNT': 10,
    'MMT_INTERNAL_DOMAINS': ['fu-berlin.de', 'example.com'],
    'MMT_USER_FILES_DIR': settings.BASE_DIR / 'user_files_test',
}
