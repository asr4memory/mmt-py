from mmt.core.media_types import AVMediaKind, av_media_kind, detect


def test_detect_prefers_contents_over_extension(tmp_path, png_bytes):
    path = tmp_path / 'image.mp3'
    path.write_bytes(png_bytes)

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


def test_av_media_kind_video():
    assert av_media_kind('video/mp4') == AVMediaKind.VIDEO


def test_av_media_kind_video_for_application_ogg():
    assert av_media_kind('application/ogg') == AVMediaKind.VIDEO


def test_av_media_kind_video_for_application_mxf():
    assert av_media_kind('application/mxf') == AVMediaKind.VIDEO


def test_av_media_kind_audio():
    assert av_media_kind('audio/mpeg') == AVMediaKind.AUDIO


def test_av_media_kind_none_for_other_type():
    assert av_media_kind('application/pdf') is None
