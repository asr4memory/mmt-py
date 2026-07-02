from bs4 import BeautifulSoup
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import SimpleTestCase


def render_messages(messages):
    html = render_to_string('_messages.html', {'messages': messages})
    return BeautifulSoup(html, 'html.parser')


class MessagesTemplateTests(SimpleTestCase):
    def test_error_and_warning_have_close_button(self):
        soup = render_messages([
            Message(constants.ERROR, 'Something went wrong.'),
            Message(constants.WARNING, 'Careful.'),
        ])
        self.assertEqual(len(soup.select('.message__close')), 2)

    def test_other_levels_have_no_close_button(self):
        soup = render_messages([
            Message(constants.SUCCESS, 'Saved.'),
            Message(constants.INFO, 'FYI.'),
        ])
        self.assertEqual(len(soup.select('.message__close')), 0)
