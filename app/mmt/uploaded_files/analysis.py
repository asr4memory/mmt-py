import hashlib
from pathlib import Path
import subprocess
import struct

SAMPLING_RATE = 100
FFMPEG_SAMPLING_RATE = 1000


def generate_file_md5(path: Path, block_size=2**20) -> str:
    m = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            buf = f.read(block_size)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def extract_waveform_data(media_file: Path) -> list[int] | None:
    # fmt: off
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(media_file),
        '-ac', '1',
        '-filter:a', f'aresample={FFMPEG_SAMPLING_RATE}',
        '-map', '0:a',
        '-c:a', 'pcm_s16le',
        '-f', 's16le',
        '-',
    ]
    # fmt: on

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
        )

        data = result.stdout
        num_samples = len(data) // 2
        samples = struct.unpack(f'<{num_samples}h', data)
        amplitudes = tuple(abs(val) for val in samples)

        batch_size = FFMPEG_SAMPLING_RATE // SAMPLING_RATE
        batch_count = num_samples // batch_size

        downsampled = [
            sum(amplitudes[x * batch_size : (x + 1) * batch_size]) // batch_size
            for x in range(batch_count)
        ]

        return downsampled
    except (subprocess.CalledProcessError, struct.error):
        return None


def extract_duration(media_file: Path) -> float | None:
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(media_file),
    ]

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None
