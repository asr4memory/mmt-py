import array
import hashlib
from pathlib import Path
import subprocess

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
    except subprocess.CalledProcessError:
        return None

    data = result.stdout
    if len(data) % 2:
        # Not a whole number of 16-bit samples.
        return None

    # array.array keeps the samples as compact 16-bit ints. struct.unpack would
    # build a tuple of Python int objects instead, costing ~18x the memory and
    # spiking badly on long recordings. Native byte order matches the
    # little-endian pcm_s16le output on the (amd64) deployment.
    samples = array.array('h')
    samples.frombytes(data)
    del data  # drop the raw-bytes copy; the compact array is enough

    batch_size = FFMPEG_SAMPLING_RATE // SAMPLING_RATE
    batch_count = len(samples) // batch_size

    return [
        sum(abs(s) for s in samples[start : start + batch_size]) // batch_size
        for start in range(0, batch_count * batch_size, batch_size)
    ]


def extract_duration(media_file: Path) -> float | None:
    cmd = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        str(media_file),
    ]

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
        )
        return float(result.stdout.strip())
    except subprocess.CalledProcessError, ValueError:
        return None
