import re
from playwright.sync_api import Page, expect


def test_has_title(page: Page):
    page.goto("http://localhost:5173/")
    expect(page).to_have_title(re.compile("MMT"))


def test_legal_notice_link(page: Page):
    page.goto("http://localhost:5173/")
    page.get_by_role("link", name="Impressum").click()
    expect(page.get_by_role("heading", name="Impressum")).to_be_visible()


def test_privacy_link(page: Page):
    page.goto("http://localhost:5173/")
    page.get_by_role("link", name="Datenschutz").click()
    expect(page.get_by_role("heading", name="Datenschutz")).to_be_visible()


def test_accessibility_link(page: Page):
    page.goto("http://localhost:5173/")
    page.get_by_role("link", name="Barrierefreiheit").click()
    expect(page.get_by_role("heading", name="Barrierefreiheit")).to_be_visible()


def test_contact_link(page: Page):
    page.goto("http://localhost:5173/")
    page.get_by_role("link", name="Kontakt").click()
    expect(page.get_by_role("heading", name="Kontakt")).to_be_visible()
