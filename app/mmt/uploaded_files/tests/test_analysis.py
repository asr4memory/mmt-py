import struct
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from mmt.uploaded_files.analysis import (
    extract_duration,
    extract_waveform_data,
    generate_file_md5,
)

MEDIA_FILE = Path('test.mp4')


def make_run_result(stdout: bytes):
    result = mock.Mock()
    result.stdout = stdout
    return result


def test_extract_waveform_data_returns_downsampled():
    # 10 samples of 200 at FFMPEG_SAMPLING_RATE=1000, SAMPLING_RATE=100 → batch_size=10 → [200]
    pcm_bytes = struct.pack('<10h', *[200] * 10)
    with mock.patch('subprocess.run', return_value=make_run_result(pcm_bytes)):
        assert extract_waveform_data(MEDIA_FILE) == [200]


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


def test_generate_file_md5():
    dummy_file_path = Path(tempfile.gettempdir()) / 'tempfile.mp4'
    with open(dummy_file_path, 'w') as f:
        f.write('Just some dummy text.')

    assert generate_file_md5(dummy_file_path) == 'd9b0cfba497e24f5f842b634f625e41c'
