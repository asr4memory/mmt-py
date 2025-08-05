from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver


class ProjectsSeleniumTests(StaticLiveServerTestCase):
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

    def sign_in(self, username: str, password: str):
        """Sign in user."""
        self.selenium.get(f"{self.live_server_url}/accounts/login/")
        username_input = self.selenium.find_element(By.NAME, "login")
        username_input.send_keys(username)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(password)
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def test_create_and_update_project(self):
        """Test creating and updating a project."""
        self.sign_in("alice", "password")
        self.selenium.find_element(
            By.CSS_SELECTOR, "a[data-testid='new-project-link']"
        ).click()

        # Create project
        form = self.selenium.find_element(
            By.CSS_SELECTOR, "form[data-testid='create-project-form']"
        )
        name_input = form.find_element(By.NAME, "name")
        name_input.send_keys("Greek Interviews")
        description_input = form.find_element(By.NAME, "description")
        description_input.send_keys(
            "Test project for uploading and transcribing Greek audio."
        )
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        el = self.selenium.find_element(By.TAG_NAME, "h1")
        self.assertEqual("Greek Interviews", el.text)

        # Edit project
        self.selenium.find_element(By.LINK_TEXT, "Edit project").click()
        form = self.selenium.find_element(
            By.CSS_SELECTOR, "form[data-testid='edit-project-form']"
        )
        name_input = form.find_element(By.NAME, "name")
        name_input.send_keys("2")
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        el = self.selenium.find_element(By.TAG_NAME, "h1")
        self.assertEqual("Greek Interviews2", el.text)

        # Delete project
        self.selenium.find_element(
            By.CSS_SELECTOR, "button[data-testid='delete-project-button']"
        ).click()
        self.selenium.switch_to.alert.accept()
        list = self.selenium.find_element(By.CSS_SELECTOR, "ul.grid")
        elements = list.find_elements(By.CSS_SELECTOR, "li.card")
        self.assertEqual(len(elements), 1)  # There was one project before.
