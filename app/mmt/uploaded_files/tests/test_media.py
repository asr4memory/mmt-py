import logging
import struct
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from mmt.uploaded_files.media import (
    detect_media_type,
    extract_duration,
    extract_waveform_data,
    generate_file_md5,
    transcode_to_web_video,
)

MEDIA_FILE = Path('test.mp4')


def make_video(
    path: Path,
    width: int = 1280,
    height: int = 720,
    duration: float = 1.0,
    audio: bool = True,
    subtitles: bool = False,
    pix_fmt: str = 'yuv420p',
) -> Path:
    """Encode a small test clip with ffmpeg and return its path."""
    cmd = [
        'ffmpeg',
        '-y',
        '-f',
        'lavfi',
        '-i',
        f'testsrc=size={width}x{height}:rate=10:duration={duration}',
    ]
    if audio:
        cmd += ['-f', 'lavfi', '-i', f'sine=frequency=440:duration={duration}']
    if subtitles:
        subtitle_path = path.parent / 'subtitles.srt'
        subtitle_path.write_text(
            '1\n00:00:00,000 --> 00:00:01,000\nA subtitle line.\n\n',
            encoding='utf-8',
        )
        cmd += ['-i', str(subtitle_path), '-c:s', 'srt']
    # -crf 0 keeps the encode lossless, which is what makes an odd height
    # representable in a pixel format without chroma subsampling.
    cmd += ['-c:v', 'libx264', '-crf', '0', '-pix_fmt', pix_fmt]
    if audio:
        cmd += ['-c:a', 'aac']
    cmd += [str(path)]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    return path


def probe_video(path: Path) -> dict[str, str]:
    """Return the first video stream's codec name, width and height."""
    cmd = [
        'ffprobe',
        '-v',
        'error',
        '-select_streams',
        'v:0',
        '-show_entries',
        'stream=codec_name,width,height',
        '-of',
        'default=noprint_wrappers=1',
        str(path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    return dict(
        line.split('=', 1) for line in result.stdout.decode().splitlines() if line
    )


def probe_stream_types(path: Path) -> list[str]:
    """Return the codec type of every stream in file order."""
    cmd = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'stream=codec_type',
        '-of',
        'csv=p=0',
        str(path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    return [line.strip() for line in result.stdout.decode().splitlines() if line.strip()]


def make_run_result(stdout: bytes):
    result = mock.Mock()
    result.stdout = stdout
    return result


def test_extract_waveform_data_returns_downsampled():
    # 10 samples of 200 at FFMPEG_SAMPLING_RATE=1000, SAMPLING_RATE=100 → batch_size=10 → [200]
    pcm_bytes = struct.pack('<10h', *[200] * 10)
    with mock.patch('subprocess.run', return_value=make_run_result(pcm_bytes)):
        assert extract_waveform_data(MEDIA_FILE) == [200]


def test_extract_waveform_data_uses_abs_and_floor_division():
    # batch 1: ten -5 → mean of abs is 5
    # batch 2: nine 0 and one 9 → 9 // 10 == 0
    pcm_bytes = struct.pack('<20h', *([-5] * 10 + [0] * 9 + [9]))
    with mock.patch('subprocess.run', return_value=make_run_result(pcm_bytes)):
        assert extract_waveform_data(MEDIA_FILE) == [5, 0]


def test_extract_waveform_data_drops_incomplete_trailing_batch():
    # 15 samples → one full batch of 10, trailing 5 dropped
    pcm_bytes = struct.pack('<15h', *([100] * 15))
    with mock.patch('subprocess.run', return_value=make_run_result(pcm_bytes)):
        assert extract_waveform_data(MEDIA_FILE) == [100]


def test_extract_waveform_data_ffmpeg_fails_returns_none():
    with mock.patch(
        'subprocess.run', side_effect=subprocess.CalledProcessError(1, 'ffmpeg')
    ):
        assert extract_waveform_data(MEDIA_FILE) is None


def test_extract_waveform_data_malformed_bytes_returns_none():
    # odd-length buffer causes struct.unpack to raise struct.error
    with mock.patch('subprocess.run', return_value=make_run_result(b'\x00' * 21)):
        assert extract_waveform_data(MEDIA_FILE) is None


def test_extract_duration_returns_float():
    with mock.patch('subprocess.run', return_value=make_run_result(b'123.456\n')):
        assert extract_duration(MEDIA_FILE) == pytest.approx(123.456)


def test_extract_duration_ffprobe_fails_returns_none():
    with mock.patch(
        'subprocess.run', side_effect=subprocess.CalledProcessError(1, 'ffprobe')
    ):
        assert extract_duration(MEDIA_FILE) is None


def test_extract_duration_unparseable_output_returns_none():
    with mock.patch('subprocess.run', return_value=make_run_result(b'N/A\n')):
        assert extract_duration(MEDIA_FILE) is None


def test_detect_media_type_returns_mime():
    with mock.patch('magic.from_file', return_value='video/ogg') as mock_from_file:
        assert detect_media_type(MEDIA_FILE) == 'video/ogg'
    mock_from_file.assert_called_once_with(str(MEDIA_FILE), mime=True)


def test_detect_media_type_returns_none_on_failure():
    with mock.patch('magic.from_file', side_effect=OSError('boom')):
        assert detect_media_type(MEDIA_FILE) is None


def test_generate_file_md5():
    dummy_file_path = Path(tempfile.gettempdir()) / 'tempfile.mp4'
    with open(dummy_file_path, 'w') as f:
        f.write('Just some dummy text.')

    assert generate_file_md5(dummy_file_path) == 'd9b0cfba497e24f5f842b634f625e41c'


def test_transcode_to_web_video_downscales_to_480p_h264(tmp_path):
    src = make_video(tmp_path / 'source.mp4', width=1280, height=720)
    dst = tmp_path / 'web' / 'source.mp4.mp4'

    assert transcode_to_web_video(src, dst) is True

    stream = probe_video(dst)
    assert stream['codec_name'] == 'h264'
    assert stream['height'] == '480'


def test_transcode_to_web_video_does_not_upscale(tmp_path):
    src = make_video(tmp_path / 'source.mp4', width=640, height=360)
    dst = tmp_path / 'web' / 'source.mp4.mp4'

    assert transcode_to_web_video(src, dst) is True

    assert probe_video(dst)['height'] == '360'


def test_transcode_to_web_video_handles_odd_height_source(tmp_path):
    src = make_video(
        tmp_path / 'source.mp4', width=640, height=361, pix_fmt='yuv444p'
    )
    dst = tmp_path / 'web' / 'source.mp4.mp4'

    assert transcode_to_web_video(src, dst) is True

    assert probe_video(dst)['height'] == '360'


def test_transcode_to_web_video_drops_subtitle_streams(tmp_path):
    src = make_video(tmp_path / 'source.mkv', width=640, height=360, subtitles=True)
    assert 'subtitle' in probe_stream_types(src)
    dst = tmp_path / 'web' / 'source.mkv.mp4'

    assert transcode_to_web_video(src, dst) is True

    assert probe_stream_types(dst) == ['video', 'audio']


def test_transcode_to_web_video_handles_source_without_audio(tmp_path):
    src = make_video(tmp_path / 'source.mp4', width=640, height=360, audio=False)
    dst = tmp_path / 'web' / 'source.mp4.mp4'

    assert transcode_to_web_video(src, dst) is True

    assert probe_stream_types(dst) == ['video']


def test_transcode_to_web_video_creates_missing_destination_dir(tmp_path):
    src = make_video(tmp_path / 'source.mp4', width=640, height=360)
    dst = tmp_path / 'web' / 'source.mp4.mp4'
    assert not dst.parent.exists()

    assert transcode_to_web_video(src, dst) is True

    assert dst.is_file()


def test_transcode_to_web_video_failure_returns_false_and_leaves_no_output(tmp_path):
    src = tmp_path / 'source.mp4'
    src.write_text('This is not a video.')
    dst = tmp_path / 'web' / 'source.mp4.mp4'

    assert transcode_to_web_video(src, dst) is False

    assert not dst.exists()
    assert list(dst.parent.iterdir()) == []


def test_transcode_to_web_video_timeout_returns_false_and_leaves_no_output(tmp_path):
    src = make_video(tmp_path / 'source.mp4', width=640, height=360)
    dst = tmp_path / 'web' / 'source.mp4.mp4'

    with mock.patch(
        'subprocess.run',
        side_effect=subprocess.TimeoutExpired(cmd='ffmpeg', timeout=1),
    ) as mock_run:
        assert transcode_to_web_video(src, dst) is False

    assert mock_run.call_args.kwargs['timeout'] > 0
    assert list(dst.parent.iterdir()) == []


def test_transcode_to_web_video_logs_stderr_on_failure(tmp_path, caplog):
    src = tmp_path / 'source.mp4'
    src.write_text('This is not a video.')
    dst = tmp_path / 'web' / 'source.mp4.mp4'

    with caplog.at_level(logging.WARNING):
        assert transcode_to_web_video(src, dst) is False

    assert str(src) in caplog.text
    assert 'Invalid data found when processing input' in caplog.text
