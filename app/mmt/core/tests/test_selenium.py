from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver


class CoreSeleniumTests(StaticLiveServerTestCase):
    fixtures = ["test_data.json"]

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

    def sign_in(self, username: str, password: str):
        """Sign in user."""
        self.selenium.get(f"{self.live_server_url}/accounts/login/")
        username_input = self.selenium.find_element(By.NAME, "login")
        username_input.send_keys(username)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(password)
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def test_welcome(self):
        """Visit welcome page."""
        self.selenium.get(f"{self.live_server_url}/")
        el = self.selenium.find_element(By.TAG_NAME, "h1")
        self.assertEqual(f"Media Management Tool", el.text)

    def test_sign_in(self):
        """Test sign in procedure."""
        self.sign_in("alice", "password")

        el = self.selenium.find_element(
            By.CSS_SELECTOR, "a[data-testid='profile-link']"
        )
        self.assertEqual("alice", el.text)

    def test_change_locale(self):
        """Test changing the user's preferred locale."""
        self.sign_in("alice", "password")
        self.selenium.find_element(
            By.CSS_SELECTOR, "a[data-testid='profile-link']"
        ).click()
        el = self.selenium.find_element(
            By.CSS_SELECTOR, "dd[data-testid='locale-display']"
        )
        self.assertEqual("English", el.text)

        self.selenium.find_element(
            By.CSS_SELECTOR, "a[data-testid='edit-profile-link']"
        ).click()
        self.selenium.find_element(By.ID, "id_locale_1").click()
        self.selenium.find_element(
            By.CSS_SELECTOR, "button[data-testid='submit-form-button']"
        ).click()
        el = self.selenium.find_element(
            By.CSS_SELECTOR, "dd[data-testid='locale-display']"
        )
        self.assertEqual("Deutsch", el.text)
