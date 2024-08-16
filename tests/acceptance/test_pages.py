import re

from playwright.sync_api import Page, expect
import pytest

BASE_URL = "http://localhost:5173/"


@pytest.mark.acceptance
def test_has_title(page: Page):
    page.goto(BASE_URL)
    expect(page).to_have_title(re.compile("MMT"))


@pytest.mark.acceptance
def test_legal_notice_link(page: Page):
    page.goto(BASE_URL)
    page.get_by_role("link", name="Impressum").click()
    expect(page.get_by_role("heading", name="Impressum")).to_be_visible()


@pytest.mark.acceptance
def test_privacy_link(page: Page):
    page.goto(BASE_URL)
    page.get_by_role("link", name="Datenschutz").click()
    expect(page.get_by_role("heading", name="Datenschutz")).to_be_visible()


@pytest.mark.acceptance
def test_accessibility_link(page: Page):
    page.goto(BASE_URL)
    page.get_by_role("link", name="Barrierefreiheit").click()
    expect(page.get_by_role("heading", name="Barrierefreiheit")).to_be_visible()


@pytest.mark.acceptance
def test_contact_link(page: Page):
    page.goto(BASE_URL)
    page.get_by_role("link", name="Kontakt").click()
    expect(page.get_by_role("heading", name="Kontakt")).to_be_visible()


@pytest.mark.acceptance
def test_login(page: Page):
    page.goto(BASE_URL)
    page.get_by_role("link", name="Anmelden").click()
    page.get_by_label("Benutzername").fill("test")
    page.get_by_label("Passwort").fill("test")
    page.get_by_role("button", name="Anmelden").click()

    # TODO: For this we need another test setup!
    # page.get_by_role("link", name="test").click()
