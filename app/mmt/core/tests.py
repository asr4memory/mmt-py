from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver


class MySeleniumTests(StaticLiveServerTestCase):
    fixtures = ["user_data.json"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.set_preference("intl.accept_languages", "en")
        options.add_argument("--headless")
        cls.selenium = WebDriver(options=options)
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_welcome(self):
        self.selenium.get(f"{self.live_server_url}/")
        el = self.selenium.find_element(By.TAG_NAME, "h1")
        self.assertEqual(f"Media Management Tool {settings.MMT_APP_VERSION}", el.text)

    def test_login(self):
        self.selenium.get(f"{self.live_server_url}/accounts/login/")
        username_input = self.selenium.find_element(By.NAME, "login")
        username_input.send_keys("alice")
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys("password")
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
