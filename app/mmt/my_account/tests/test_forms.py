import pytest
from django.urls import reverse

from mmt.my_account.forms import CustomSignupForm


def test_signup_honeypot_field_has_no_inline_style():
    form = CustomSignupForm()
    widget = form.fields['address'].widget

    assert 'style' not in widget.attrs
    assert widget.attrs['class'] == 'u-visually-hidden'


@pytest.mark.django_db
def test_signup_page_does_not_render_the_honeypot_off_screen(client):
    response = client.get(reverse('account_signup'))
    html = response.content.decode()

    assert 'id="id_address"' in html
    assert '-99999px' not in html
