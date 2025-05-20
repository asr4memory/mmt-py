from django import test


class ExampleTestMixin:
    def assertClearSiteData(self, response, value=None):
        if value is None:
            value = ["*"]

        self.assertEqual(
            response.get("Clear-Site-Data", ""),
            ", ".join(f'"{v}"' for v in value),
        )


class SimpleTestCase(ExampleTestMixin, test.SimpleTestCase):
    pass


class TestCase(ExampleTestMixin, test.TestCase):
    pass


class TransactionTestCase(ExampleTestMixin, test.TransactionTestCase):
    pass


class LiveServerTestCase(ExampleTestMixin, test.LiveServerTestCase):
    pass
