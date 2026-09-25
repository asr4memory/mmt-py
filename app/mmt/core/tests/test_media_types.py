import base64

from mmt.core.media_types import category, detect

# A 1x1 pixel PNG image.
PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
    '60e6kgAAAABJRU5ErkJggg=='
)


def test_detect_prefers_contents_over_extension(tmp_path):
    path = tmp_path / 'image.mp3'
    path.write_bytes(PNG_BYTES)

    assert detect(path) == 'image/png'


def test_detect_falls_back_to_extension_for_unrecognised_contents(tmp_path):
    path = tmp_path / 'recording.mp3'
    path.write_bytes(bytes(16))

    assert detect(path) == 'audio/mpeg'


def test_detect_falls_back_to_extension_for_unreadable_file(tmp_path):
    assert detect(tmp_path / 'missing.pdf') == 'application/pdf'


def test_detect_falls_back_to_default(tmp_path):
    path = tmp_path / 'recording'
    path.write_bytes(bytes(16))

    assert detect(path) == 'application/octet-stream'
    assert detect(path, default='audio/wav') == 'audio/wav'


def test_category_video():
    assert category('video/mp4') == 'video'


def test_category_video_for_application_ogg():
    assert category('application/ogg') == 'video'


def test_category_video_for_application_mxf():
    assert category('application/mxf') == 'video'


def test_category_audio():
    assert category('audio/mpeg') == 'audio'


def test_category_pdf():
    assert category('application/pdf') == 'pdf'


def test_category_image():
    assert category('image/png') == 'image'


def test_category_text():
    assert category('text/plain') == 'text'


def test_category_falls_back_to_media_type():
    """An unrecognised type keeps its media type so no information is lost."""
    assert category('application/zip') == 'application/zip'
