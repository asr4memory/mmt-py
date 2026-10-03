import base64

import pytest


@pytest.fixture
def png_bytes():
    """A 1x1 pixel PNG image, for tests that need contents libmagic recognises."""
    return base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
        '60e6kgAAAABJRU5ErkJggg=='
    )
