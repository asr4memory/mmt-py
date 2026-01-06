import tempfile
import unittest
from pathlib import Path

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver

from mmt.projects.models import Project


class ProjectsSeleniumTests(StaticLiveServerTestCase):
    fixtures = ['test_data.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.set_preference('intl.accept_languages', 'en')
        options.add_argument('--headless')
        cls.selenium = WebDriver(options=options)
        cls.selenium.implicitly_wait(10)
        cls.selenium.set_window_size(1920, 1080)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def sign_in(self, username: str, password: str):
        """Sign in user."""
        self.selenium.get(f'{self.live_server_url}/accounts/login/')
        username_input = self.selenium.find_element(By.NAME, 'login')
        username_input.send_keys(username)
        password_input = self.selenium.find_element(By.NAME, 'password')
        password_input.send_keys(password)
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def test_create_and_update_project(self):
        """Test creating and updating a project."""
        self.sign_in('alice', 'password')
        self.selenium.find_element(
            By.CSS_SELECTOR, "a[data-testid='projects-link']"
        ).click()
        self.selenium.find_element(
            By.CSS_SELECTOR, "a[data-testid='new-project-link']"
        ).click()

        # Create project
        form = self.selenium.find_element(
            By.CSS_SELECTOR, "form[data-testid='create-project-form']"
        )
        title_input = form.find_element(By.NAME, 'title')
        title_input.send_keys('Greek Interviews')
        description_input = form.find_element(By.NAME, 'description')
        description_input.send_keys(
            'Test project for uploading and transcribing Greek audio.'
        )
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        el = self.selenium.find_element(By.TAG_NAME, 'h1')
        self.assertEqual('Greek Interviews', el.text)

        # Edit project
        self.selenium.find_element(By.LINK_TEXT, 'Project settings').click()
        form = self.selenium.find_element(
            By.CSS_SELECTOR, "form[data-testid='edit-project-form']"
        )
        title_input = form.find_element(By.NAME, 'title')
        title_input.send_keys('2')
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        el = self.selenium.find_element(By.TAG_NAME, 'h1')
        self.assertEqual('Greek Interviews2', el.text)

        # Delete project
        self.selenium.find_element(By.LINK_TEXT, 'Project settings').click()
        self.selenium.find_element(
            By.CSS_SELECTOR, "button[data-testid='delete-project-button']"
        ).click()
        self.selenium.switch_to.alert.accept()
        list = self.selenium.find_element(By.CSS_SELECTOR, 'ul.grid')
        elements = list.find_elements(By.CSS_SELECTOR, 'li.card')
        self.assertEqual(len(elements), 1)  # There was one project before.

    @unittest.skip
    def test_uploading_files(self):
        """Test uploading files to an existing project."""
        self.sign_in('alice', 'password')
        self.selenium.get(f'{self.live_server_url}/')

        # Prepare: Create project directory.
        project = Project.objects.first()

        # Remove file from previous tests
        file_path = project.upload_directory / 'tempfile.mp4'
        file_path.unlink(missing_ok=True)

        # Navigate to existing project detail page.
        self.selenium.find_element(By.LINK_TEXT, 'Projects').click()

        link = self.selenium.find_element(
            By.CSS_SELECTOR, "a[data-testid='project-card']"
        )
        link.click()

        heading = self.selenium.find_element(By.TAG_NAME, 'h1')
        self.assertEqual('Test project', heading.text)
        self.selenium.find_element(By.LINK_TEXT, 'Upload files').click()

        # Create dummy file.
        dummy_file_path = Path(tempfile.gettempdir()) / 'tempfile.mp4'
        with open(dummy_file_path, 'w') as f:
            f.write('Just some dummy text.')

        # Fill out upload form.
        form = self.selenium.find_element(
            By.CSS_SELECTOR, "form[data-testid='upload-files-form']"
        )
        file_input = form.find_element(By.NAME, 'files')
        file_input.send_keys(str(dummy_file_path))
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Check detail page
        p = self.selenium.find_element(
            By.CSS_SELECTOR, "p[data-testid='uploaded-files-count']"
        )
        self.assertEqual('This project has 1 uploaded files.', p.text)

        table_row = self.selenium.find_element(By.CSS_SELECTOR, 'table > tbody > tr')
        cell1 = table_row.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1)')
        self.assertEqual('tempfile.mp4', cell1.text)
        cell2 = table_row.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2)')
        self.assertEqual('video/mp4', cell2.text)
        cell3 = table_row.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)')
        self.assertEqual('21 bytes', cell3.text)
        cell4 = table_row.find_element(By.CSS_SELECTOR, 'td:nth-of-type(4)')
        self.assertEqual('Created', cell4.text)  # Actually should be "Complete"
        cell5 = table_row.find_element(By.CSS_SELECTOR, 'td:nth-of-type(5)')
        self.assertEqual('today', cell5.text)

        # Go on examining and finally deleting the uploaded file.
        table_row.find_element(By.LINK_TEXT, 'tempfile.mp4').click()
        heading = self.selenium.find_element(By.TAG_NAME, 'h1')
        self.assertEqual('tempfile.mp4', heading.text)
        self.selenium.find_element(
            By.CSS_SELECTOR, "button[data-testid='delete-button']"
        ).click()
        self.selenium.switch_to.alert.accept()

        p = self.selenium.find_element(
            By.CSS_SELECTOR, "p[data-testid='uploaded-files-count']"
        )
        self.assertEqual('No files have been uploaded to this project yet.', p.text)

        tables = self.selenium.find_elements(By.TAG_NAME, 'table')
        self.assertEqual(0, len(tables))

        # Remove temporary file.
        dummy_file_path.unlink()
