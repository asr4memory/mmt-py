import tempfile
import unittest
from pathlib import Path

import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

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


#
# Tab panel swapping
#
# These tests need the JavaScript bundle. In the test environment django-vite
# runs in dev mode, so the page loads its assets from the Vite dev server:
# run `npm run dev` alongside them.
#
@pytest.fixture(scope='session')
def selenium_driver():
    options = Options()
    options.set_preference('intl.accept_languages', 'en')
    options.add_argument('--headless')
    driver = WebDriver(options=options)
    driver.implicitly_wait(10)
    driver.set_window_size(1920, 1080)
    yield driver
    driver.quit()


def sign_in(driver, live_server, username: str, password: str) -> None:
    driver.get(f'{live_server.url}/accounts/login/')
    driver.find_element(By.NAME, 'login').send_keys(username)
    driver.find_element(By.NAME, 'password').send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()


def by_testid(value: str) -> tuple[str, str]:
    return (By.CSS_SELECTOR, f"[data-testid='{value}']")


@pytest.fixture
def project_page(selenium_driver, live_server, transactional_db):
    """Sign alice in and open the detail page of her project."""
    call_command('loaddata', 'test_data.json')
    project = Project.objects.first()
    # The fixture only carries database rows; the downloads tab reads the
    # project's download directory.
    project.ensure_directories()
    sign_in(selenium_driver, live_server, 'alice', 'password')
    selenium_driver.get(f'{live_server.url}/projects/{project.pk}/')
    return project


def test_clicking_a_tab_swaps_the_panel_without_a_page_load(
    selenium_driver, project_page
):
    """Clicking a tab replaces the panel instead of loading a new page."""
    # A variable on window survives a swap and is lost on a page load, so it is
    # what distinguishes the two.
    selenium_driver.execute_script('window.pageWasNotReloaded = true;')

    selenium_driver.find_element(*by_testid('downloads-tab')).click()

    WebDriverWait(selenium_driver, 10).until(
        expected_conditions.presence_of_element_located(
            by_testid('downloadable-files-count')
        )
    )
    assert selenium_driver.find_elements(*by_testid('uploaded-files-count')) == []
    assert selenium_driver.current_url.endswith(
        f'/projects/{project_page.pk}/downloads/'
    )
    assert selenium_driver.execute_script('return window.pageWasNotReloaded;') is True
    # The tab bar is outside the swapped element, so the active tab marker is
    # moved by the client.
    downloads_tab = selenium_driver.find_element(*by_testid('downloads-tab'))
    uploaded_files_tab = selenium_driver.find_element(*by_testid('uploaded-files-tab'))
    assert downloads_tab.get_attribute('aria-current') == 'page'
    assert uploaded_files_tab.get_attribute('aria-current') is None


def test_back_button_returns_to_the_previous_tab(selenium_driver, project_page):
    """hx-push-url makes the browser's Back button return to the previous tab."""
    selenium_driver.find_element(*by_testid('downloads-tab')).click()
    WebDriverWait(selenium_driver, 10).until(
        expected_conditions.presence_of_element_located(
            by_testid('downloadable-files-count')
        )
    )

    selenium_driver.back()

    WebDriverWait(selenium_driver, 10).until(
        expected_conditions.presence_of_element_located(by_testid('uploaded-files-count'))
    )
    assert selenium_driver.current_url.endswith(f'/projects/{project_page.pk}/')


def test_back_after_a_history_cache_miss_keeps_the_layout(
    selenium_driver, project_page
):
    """A restore that has to ask the server again returns a full page."""
    selenium_driver.find_element(*by_testid('downloads-tab')).click()
    WebDriverWait(selenium_driver, 10).until(
        expected_conditions.presence_of_element_located(
            by_testid('downloadable-files-count')
        )
    )
    # On a cache hit htmx restores its snapshot and never asks the server, which
    # would hide the behavior this test is about.
    selenium_driver.execute_script('sessionStorage.clear();')

    selenium_driver.back()

    WebDriverWait(selenium_driver, 10).until(
        expected_conditions.presence_of_element_located(by_testid('uploaded-files-tab'))
    )
