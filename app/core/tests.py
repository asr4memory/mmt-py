from django.test import TestCase


class CoreTests(TestCase):
    def test_welcome_page(self):
        """Welcome page works"""
        response = self.client.get("/", follow=True)

        self.assertContains(
            response, "<h1>Administration software for media files</h1>", html=True
        )
